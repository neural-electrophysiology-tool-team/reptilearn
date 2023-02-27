import io from 'socket.io-client';
import React from 'react';

import { socketio_url } from './api';

export const socket = io(socketio_url);
export const SocketContext = React.createContext();