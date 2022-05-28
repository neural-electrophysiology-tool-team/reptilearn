import React from 'react';
import {SocketContext} from '../socket.js';
import RLButton from './ui/button.js';
import { Bar } from './ui/bar.js';

export const LogView = () => {
    const logContainer = React.useRef((localStorage.log || '')  +
                                      (localStorage.log ? '\n===================' : ''));
    const textarea_ref = React.useRef();
    const [logMsg, setLogMsg] = React.useState(logContainer.current);
    
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
        localStorage.log = logContainer.current; 
        setLogMsg(null);
    };

    return (
	<div className='flex flex-col h-full'>
          <Bar title="Log" className="flex flex-0">
            <RLButton.BarButton onClick={clear_log} text="Clear"/>
          </Bar>
          <textarea value={logContainer.current}
                    readOnly
                    className="whitespace-pre py-0 px-1 flex flex-1 w-full font-mono overflow-y-auto"
		    ref={textarea_ref}/>
        </div>
    );
};
