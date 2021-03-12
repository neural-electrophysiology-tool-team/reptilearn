import React from 'react';
import {SocketContext} from './socket.js';

export const LogView = () => {
    const logContainer = React.useRef("");

    const socket = React.useContext(SocketContext);

    React.useEffect(() => {
	socket.on("log", msg => logContainer.current += msg + "\n");
    }, [socket]);

    return (
        <div className="component">
          Log:<br/>
          <textarea value={logContainer.current}
                    rows="10"
                    cols="80"
                    readOnly/>
        </div>
    );
};
