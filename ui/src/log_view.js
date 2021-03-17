import React from 'react';
import {SocketContext} from './socket.js';

export const LogView = () => {
    const logContainer = React.useRef("System log\n==========\n");
    const textarea_ref = React.useRef();
    const [logMsg, setLogMsg] = React.useState(null);
    
    const socket = React.useContext(SocketContext);

    React.useEffect(() => {
        const listener = msg => {	   
            logContainer.current += "\n" + msg ;
            setLogMsg(msg);
	    if (textarea_ref.current !== null)
		textarea_ref.current.scrollTop = textarea_ref.current.scrollHeight;
        };
        
	socket.on("log", listener);
        return () => { // cleanup
            socket.off("log", listener);
        };
    }, [socket]);

    return (
          <textarea value={logContainer.current}
                    readOnly
                    className="log_view pane-content"
		    ref={textarea_ref}/>
    );
};
