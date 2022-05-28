import React from 'react';
import RLModal from './ui/modal.js';
import { api_url } from '../config.js';
import { RLListbox } from './ui/list_box.js';
import RLButton from './ui/button.js';

export const ArchiveView = ({ sessions, setOpen, open, close_session_list }) => {
    const [archives, setArchives] = React.useState(null);
    const [selection, setSelection] = React.useState([]);

    React.useEffect(() => {
        fetch(api_url + "/config/archive_dirs")
            .then((res) => res.json())
            .then((res) => setArchives(res));
    }, [open]);

    const copy = () => {
        fetch(api_url + "/sessions/archive/copy", {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                archives: selection,
                sessions: sessions,
            })
        })
            .then(() => {
                setOpen(false);
                if (close_session_list) {
                    close_session_list();
                }
            });
    };

    return (
        <RLModal sizeClasses="w-1/6" open={open} setOpen={setOpen} header={`Archive ${sessions.length} sessions`} actions={
            <React.Fragment>
                <RLButton.ModalButton onClick={copy} disabled={selection.length === 0}>Copy</RLButton.ModalButton>
                <RLButton.ModalButton onClick={() => setOpen(false)}>Cancel</RLButton.ModalButton>
            </React.Fragment>
        }>
            <RLListbox value={selection} onChange={setSelection} header="Select destination(s)" multiple loading={!archives}>
                {!archives ? null : Object.entries(archives).map((dest) => (
                    <RLListbox.CheckedOption key={dest} value={dest[0]} label={dest[0]} title={dest[1]}/>                    
                ))}
            </RLListbox>
        </RLModal>
    );
};
