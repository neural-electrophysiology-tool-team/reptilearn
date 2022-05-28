import React from 'react';

import { api_url } from '../config.js';
import { ArchiveView } from './archive_view.js';
import { DeleteSessionModal } from './delete_session_view.js';
import RLButton from './ui/button.js';
import RLModal from './ui/modal.js';

export const SessionListView = ({ onSelect, setOpen, open, selectable, manageable }) => {
    const [sessionList, setSessionList] = React.useState(null);
    const [selectedSessions, setSelectedSessions] = React.useState([]);
    const [openArchiveModal, setOpenArchiveModal] = React.useState(false);
    const [openDeleteModal, setOpenDeleteModal] = React.useState(false);
    const [reload, setReload] = React.useState(true);

    React.useEffect(() => {
        if (!open || !reload) {
            return false;
        }

        setReload(false);
        setSelectedSessions([]);
        fetch(api_url + "/session/list")
            .then(res => res.json())
            .then((res) => {
                setSessionList(res);
            });
    }, [open, reload]);

    const toggle_session = (session) => {
        const ss = [...selectedSessions];
        const s_idx = ss.indexOf(session);

        if (s_idx !== -1) {
            ss.splice(s_idx, 1);
        }
        else {
            ss.push(session);
        }
        console.log(ss);
        setSelectedSessions(ss);
    };

    const open_archive_modal = () => {
        setOpenArchiveModal(true);
    };

    // RENDER

    const items = sessionList ? sessionList.map(s => {
        return (
            <tr key={s}>
                {manageable ? (
                    <td>
                        <input type="checkbox" onChange={() => toggle_session(s)} />
                    </td>
                ) : null}
                <td>
                    {selectable ?
                        <button onClick={() => onSelect(s[2])}>{s[0]}</button>
                        : s[0]
                    }
                </td>
                <td>
                    {s[1]}
                </td>
            </tr>
        );
    }).reverse() : undefined;

    const content = items ? (
        <table>
            <tbody>
                {items}
            </tbody>

        </table>
    ) : "Loading...";

    return (
        <RLModal sizeClasses="max-w-lg w-5/6" open={open} setOpen={setOpen} header={selectable ? 'Select session' : 'Sessions'} actions={
            <React.Fragment>
                {
                    manageable ? (
                        <React.Fragment>
                            <RLButton.ModalButton
                                onClick={open_archive_modal}
                                disabled={selectedSessions.length === 0}>
                                {/* <Icon name="archive" /> */}
                                Archive
                            </RLButton.ModalButton>
                            <RLButton.ModalButton
                                onClick={() => setOpenDeleteModal(true)}
                                disabled={selectedSessions.length === 0}>
                                {/* <Icon name="delete" /> */}
                                Delete
                            </RLButton.ModalButton>
                        </React.Fragment>
                    ) : null
                }
                <RLButton.ModalButton onClick={() => setOpen(false)}>{manageable ? 'Close' : 'Cancel'}</RLButton.ModalButton>
            </React.Fragment>
        }>
            {content /*scrolling*/}
            <ArchiveView sessions={selectedSessions}
                setOpen={setOpenArchiveModal}
                open={openArchiveModal} />
            <DeleteSessionModal sessions={selectedSessions}
                setOpen={setOpenDeleteModal}
                onDelete={() => setReload(true)}
                open={openDeleteModal} />

        </RLModal>
    );
};
