import io from 'socket.io-client';
import { server_url } from './config.js';
import React from 'react';

export const socket = io("localhost:5000");
export const SocketContext = React.createContext();

socket.on('connect', () => { console.log("SocketIO connected."); });
