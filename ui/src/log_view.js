import React from 'react';
import {SocketContext} from './socket.js';

export const LogView = () => {
    const logContainer = React.useRef(localStorage.log || "");
    const textarea_ref = React.useRef();
    const [logMsg, setLogMsg] = React.useState(null);
    
    const socket = React.useContext(SocketContext);

    React.useEffect(() => {
        const listener = msg => {
            let is_scrolled_to_bottom = null;
	    if (textarea_ref.current !== null) {
                const textarea = textarea_ref.current;
                is_scrolled_to_bottom = textarea.scrollHeight - textarea.clientHeight <= textarea.scrollTop + 1;
            }
            
            if (logContainer.current !== "")
                logContainer.current += "\n";
            logContainer.current += msg;

	    localStorage.log = logContainer.current; 
            setLogMsg(msg);

	    if (textarea_ref.current !== null) {
                if (is_scrolled_to_bottom)
		    textarea_ref.current.scrollTop = textarea_ref.current.scrollHeight;
            }
        };

	socket.on("log", listener);

	// scroll to top after loading from localstorage
	textarea_ref.current.scrollTop = textarea_ref.current.scrollHeight;
	
        return () => { // cleanup
            socket.off("log", listener);
        };
    }, [socket]);

    const clear_log = () => {
        logContainer.current = "";
        setLogMsg(null);
    };

    return (
	<React.Fragment>
          <div className="section_header">
            <span className="title">Log</span>
            <button onClick={clear_log}>Clear</button>
          </div>
          <textarea value={logContainer.current}
                    readOnly
                    className="log_view"
		    ref={textarea_ref}/>
        </React.Fragment>
    );
};
