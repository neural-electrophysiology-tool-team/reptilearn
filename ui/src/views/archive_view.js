import React from 'react';
import RLModal from './ui/modal.js';
import { RLListbox } from './ui/list_box.js';
import RLButton from './ui/button.js';
import { api } from '../api.js';

export const ArchiveView = ({ sessions, setOpen, open, close_session_list }) => {
    const [archives, setArchives] = React.useState(null);
    const [selection, setSelection] = React.useState([]);

    React.useEffect(() => {
        api.get_config("archive_dirs")
            .then((res) => res.json())
            .then((res) => setArchives(res));
    }, [open]);

    const copy = () => {
        api.sessions.archive.copy(sessions, selection)
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
