import io from 'socket.io-client';
import { socketio_url } from './config.js';
import React from 'react';

console.log(socketio_url);
export const socket = io(socketio_url);
export const SocketContext = React.createContext();

socket.on('connect', () => { console.log("SocketIO connected."); });
