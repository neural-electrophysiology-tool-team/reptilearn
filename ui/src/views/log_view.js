import React from 'react';
import RLButton from './ui/button.js';
import { Bar } from './ui/bar.js';
import { RLSpinner } from './ui/spinner.js';
import { api } from '../api.js';
import { useDispatch, useSelector } from 'react-redux';
import { setLog } from '../store/reptilearn_slice.js';

export const LogView = () => {
    const textarea_ref = React.useRef();
    const log = useSelector((state) => state.reptilearn.log);
    const dispatch = useDispatch();

    React.useEffect(() => {
        if (textarea_ref.current) {
            textarea_ref.current.scrollTop = textarea_ref.current.scrollHeight;
        }
    }, [textarea_ref]);
    
    React.useEffect(() => {
        let is_scrolled_to_bottom = textarea_ref.current
            ? textarea_ref.current.scrollHeight - textarea_ref.current.clientHeight <= textarea_ref.current.scrollTop + 50
            : null;

        setTimeout(() => {
            if (textarea_ref.current) {
                if (is_scrolled_to_bottom || textarea_ref.current.value.length === 0)
                    textarea_ref.current.scrollTop = textarea_ref.current.scrollHeight;
            }    
        }, 0);
        
    }, [log]);

    const clear_log = async () => {
        await api.log.clear_buffer();
        dispatch(setLog([]));
    };

    return (
        <div className='flex flex-col h-full'>
            <Bar title="Log" className="flex flex-0">
                <RLButton.BarButton onClick={clear_log} text="Clear" disabled={!log} />
            </Bar>
            {!log
                ? <RLSpinner>Loading...</RLSpinner>
                : (<textarea value={log.join('\n')}
                    readOnly
                    className="whitespace-pre py-0 px-1 flex flex-1 w-full font-mono overflow-y-auto text-[15px]"
                    ref={textarea_ref} />
                )}
        </div>
    );
};
