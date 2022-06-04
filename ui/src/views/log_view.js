import React from 'react';
import { SocketContext } from '../socket.js';
import RLButton from './ui/button.js';
import { Bar } from './ui/bar.js';
import { api_url } from '../config.js';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

export const LogView = () => {
    const socket = React.useContext(SocketContext);
    const textarea_ref = React.useRef();
    const log = React.useRef(null);
    const [listenerSetup, setListenerSetup] = React.useState(false)
    const [logUpdated, setLogUpdated] = React.useState(new Date());
    const [bufferLength, setBufferLength] = React.useState(1000);

    const listener = (log_line) => {
        if (log.current !== null) {
            let is_scrolled_to_bottom = textarea_ref.current
                ? textarea_ref.current.scrollHeight - textarea_ref.current.clientHeight <= textarea_ref.current.scrollTop + 50
                : null;

            if (log.current.length >= bufferLength) {
                const [head, ...new_log] = log.current;
                log.current = [...new_log, log_line];
            } else {
                log.current = [...log.current, log_line];
            }            
            
            setLogUpdated(new Date());
            
            setTimeout(() => {
                if (textarea_ref.current) {
                    if (is_scrolled_to_bottom)
                        textarea_ref.current.scrollTop = textarea_ref.current.scrollHeight;
                }    
            }, 0);
        }
    };

    React.useEffect(() => {
        if (socket.hasListeners('log')) {
            return;
        }

        socket.on('log', listener);

        fetch(api_url + '/log/get_buffer')
            .then((res) => res.json())
            .then((log_buffer) => {
                log.current = log_buffer;
                // scroll to top after loading log buffer
                if (textarea_ref.current) {
                    textarea_ref.current.scrollTop = textarea_ref.current.scrollHeight;
                }

                return fetch(api_url + '/config/log_buffer_size')
            })
            .then((res) => res.json())
            .then((val) => {
                setBufferLength(val)
                setListenerSetup(true);                
            });
    });

    React.useEffect(() => {
        if (textarea_ref.current && listenerSetup) {
            textarea_ref.current.scrollTop = textarea_ref.current.scrollHeight;
            setListenerSetup(false);
        }
    }, [listenerSetup, textarea_ref]);

    const clear_log = async () => {
        await fetch(api_url + '/log/clear_buffer');
        log.current = [];
        setLogUpdated(new Date());
    };

    return (
        <div className='flex flex-col h-full'>
            <Bar title="Log" className="flex flex-0">
                <RLButton.BarButton onClick={clear_log} text="Clear" disabled={!log?.current} />
            </Bar>
            {(!log?.current)
                ? <div><FontAwesomeIcon icon="spinner" className="animate-spin mx-1" />Loading...</div>
                : (<textarea value={log.current.join('\n')}
                    readOnly
                    className="whitespace-pre py-0 px-1 flex flex-1 w-full font-mono overflow-y-auto text-[15px]"
                    ref={textarea_ref} />
                )}
        </div>
    );

};
