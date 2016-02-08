# -*- coding: utf-8 -*-

# Copyright (C) 2016, Maximilian Köhl <mail@koehlma.de>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License version 3 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function, unicode_literals

from .. import error, handle
from ..library import ffi, lib

from . import stream

__all__ = ['Pipe']


class PipeConnectRequest(stream.ConnectRequest):
    uv_request_init = lib.uv_pipe_connect

    def __init__(self, pipe, path, on_connect=None):
        super(PipeConnectRequest, self).__init__(pipe, (path.encode(),),
                                                 on_connect=on_connect)


@handle.HandleTypes.PIPE
class Pipe(stream.Stream):
    """
    Pipe handles provide an abstraction over local domain sockets
    on Unix and named pipes on Windows.

    :raises uv.UVError: error while initializing the handle

    :param loop: event loop the handle should run on
    :param ipc: pipe should have inter process communication support not

    :type loop: uv.Loop
    :type ipc: bool
    """

    __slots__ = ['uv_pipe']

    uv_handle_type = 'uv_pipe_t*'
    uv_handle_init = lib.uv_pipe_init

    def __init__(self, loop=None, ipc=False):
        super(Pipe, self).__init__(loop, ipc, (int(ipc), ))
        self.uv_pipe = self.base_handle.uv_object

    def open(self, fd):
        """
        Open an existing file descriptor as a pipe.

        :raises uv.UVError: error while opening the handle
        :raises uv.ClosedHandleError: handle has already been closed or is closing

        :param fd: file descriptor
        :type fd: int
        """
        if self.closing:
            raise error.ClosedHandleError()
        code = lib.cross_uv_pipe_open(self.uv_pipe, fd)
        if code != error.StatusCodes.SUCCESS:
            raise error.UVError(code)

    @property
    def pending_count(self):
        """
        Number of pending streams to receive.

        :readonly: True
        :rtype: int
        """
        if self.closing:
            return 0
        return lib.uv_pipe_pending_count(self.uv_pipe)

    @property
    def pending_type(self):
        """
        Type of first pending stream. This returns a subclass of :class:`uv.Stream`.

        :raises uv.ClosedHandleError: handle has already been closed or is closing

        :readonly: True
        :rtype: type
        """
        if self.closing:
            raise error.ClosedHandleError()
        return handle.HandleTypes(lib.uv_pipe_pending_type(self.uv_pipe)).cls

    def pending_accept(self):
        """
        Accept a pending stream.

        :raises uv.UVError: error while accepting stream
        :raises uv.ClosedHandleError: handle has already been closed or is closing

        :rtype: uv.Stream
        """
        return self.accept(cls=self.pending_type)

    def pending_instances(self, amount):
        """
        Set the number of pending pipe instance handles when the pipe server is
        waiting for connections.

        :param amount: amount of pending instances
        :type amount: int
        """
        lib.uv_pipe_pending_instances(self.uv_pipe, amount)

    @property
    def family(self):
        return socket.AF_UNIX if is_posix else None

    @property
    def sockname(self):
        """
        Name of the Unix domain socket or the named pipe.

        :raises uv.UVError: error while receiving sockname
        :raises uv.ClosedHandleError: handle has already been closed or is closing

        :readonly: True
        :rtype: unicode
        """
        if self.closing:
            raise error.ClosedHandleError()
        c_buffer = ffi.new('char[]', 255)
        c_size = ffi.new('size_t*', 255)
        code = lib.uv_pipe_getsockname(self.uv_pipe, c_buffer, c_size)
        if code == error.StatusCodes.ENOBUFS:
            c_buffer = ffi.new('char[]', c_size[0])
            code = lib.uv_pipe_getsockname(self.uv_pipe, c_buffer, c_size)
        if code != error.StatusCodes.SUCCESS:
            raise error.UVError(code)
        return ffi.string(c_buffer, c_size[0]).decode()

    @property
    def peername(self):
        """
        Name of the Unix domain socket or the named pipe to which the handle is connected.

        :raises uv.UVError: error while receiving peername
        :raises uv.ClosedHandleError: handle has already been closed or is closing

        :readonly: True
        :rtype: unicode
        """
        if self.closing:
            raise error.ClosedHandleError()
        c_buffer = ffi.new('char[]', 255)
        c_size = ffi.new('size_t*', 255)
        code = lib.uv_pipe_getpeername(self.uv_pipe, c_buffer, c_size)
        if code == error.StatusCodes.ENOBUFS:
            c_buffer = ffi.new('char[]', c_size[0])
            code = lib.uv_pipe_getpeername(self.uv_pipe, c_buffer, c_size)
        if code != error.StatusCodes.SUCCESS:
            raise error.UVError(code)
        return ffi.string(c_buffer, c_size[0]).decode()

    def bind(self, path):
        """
        Bind the pipe to a file path (Unix) or a name (Windows).

        :raises uv.UVError: error while binding to `path`
        :raises uv.ClosedHandleError: handle has already been closed or is closing

        :param path: path to bind to
        :type path: unicode
        """
        if self.closing:
            raise error.ClosedHandleError()
        code = lib.uv_pipe_bind(self.uv_pipe, path.encode())
        if code != error.StatusCodes.SUCCESS:
            raise error.UVError(code)

    def connect(self, path, on_connect=None):
        """
        Connect to the given Unix domain socket or named pipe.

        :raises uv.ClosedHandleError: handle has already been closed or is closing

        :param path: path to connect to
        :param on_connect: callback called after connection has been established

        :type path: unicode
        :type on_connect: ((uv.ConnectRequest, uv.StatusCode) -> None) |
                          ((Any, uv.ConnectRequest, uv.StatusCode) -> None)

        :returns: connect request
        :rtype: uv.ConnectRequest
        """
        return PipeConnectRequest(self, path, on_connect)
