import React from 'react';

import { api_url } from '../config.js';
import RLButton from './ui/button.js';
import RLModal from './ui/modal.js';

export const DeleteSessionModal = ({ session, sessions, open, setOpen, onDelete }) => {
    const [dataRoot, setDataRoot] = React.useState(null);

    React.useEffect(() => {
        fetch(api_url + "/config/session_data_root")
            .then((res) => res.json())
            .then((res) => setDataRoot(res));
    }, [open]);

    if (session) {
        const data_dir = session.data_dir.split('/');
        sessions = [['', '', data_dir[data_dir.length - 1]]];
    }
    else if (!sessions) {
        return null;
    }

    const delete_sessions = () => {
        setOpen(false);
        fetch(api_url + "/sessions/delete", {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(sessions),
        })
            .then(() => {
                onDelete?.();
            });
    };

    return (
        <RLModal open={open} setOpen={setOpen} header="Are you sure?" sizeClasses="w-2/6" actions={
            <React.Fragment>
                <RLButton.ModalButton colorClasses="text-red-500" onClick={delete_sessions}>Yes</RLButton.ModalButton>
                <RLButton.ModalButton onClick={() => setOpen(false)}>No</RLButton.ModalButton>
            </React.Fragment>
        }>
            <div className='flex flex-col'>
                <div>The following data directories will be deleted:</div>
                <ul className='pt-2'>
                    {sessions.map((s) => <li className="ml-5" key={s}>{dataRoot + '/' + s[2]}</li>)}
                </ul>
            </div>
        </RLModal>
    );
};

