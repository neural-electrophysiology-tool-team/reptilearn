import React from 'react';
import { api } from '../api.js';

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
        if (!open) {
            return;
        }

        setReload(false);
        setSelectedSessions([]);
        api.session.get_list()
            .then((res) => {
                setSessionList(res);
            });
    }, [open]);

    React.useEffect(() => {
        if (!reload) {
            return;
        }

        setReload(false);
        setSelectedSessions([]);
        fetch(api_url + "/session/list")
            .then(res => res.json())
            .then((res) => {
                setSessionList(res);
            });
    }, [reload]);

    const toggle_session = (session) => {
        const ss = [...selectedSessions];
        const s_idx = ss.indexOf(session);

        if (s_idx !== -1) {
            ss.splice(s_idx, 1);
        }
        else {
            ss.push(session);
        }

        setSelectedSessions(ss);
    };

    const open_archive_modal = () => {
        setOpenArchiveModal(true);
    };

    const content = sessionList ? (
        <table className="table w-full h-fit border-gray-300 border-hidden rounded-md shadow-md overflow-y-scroll flex-grow">
            <tbody>
                {sessionList.map(s => {
                    return (
                        <tr key={s} className="border-gray-200 border border-y w-full">
                            {manageable ? (
                                <td className="px-2 py-2  ">
                                    <input type="checkbox" onChange={() => toggle_session(s)} />
                                </td>
                            ) : null}
                            <td className="px-2 py-2">
                                {selectable ?
                                    <button onClick={() => onSelect(s[2])} className="text-blue-700 hover:decoration-blue-700 hover:underline">{s[0]}</button>
                                    : s[0]
                                }
                            </td>
                            <td className="px-2 py-2">
                                {s[1]}
                            </td>
                        </tr>
                    );
                }).reverse()}
            </tbody>

        </table>
    ) : "Loading...";

    return (
        <RLModal sizeClasses="max-w-lg w-5/6 max-h-[75vh]" open={open} setOpen={setOpen} header={selectable ? 'Select session' : 'Sessions'} contentOverflowClass="overflow-hidden" actions={
            <React.Fragment>
                {
                    manageable ? (
                        <>
                            <RLButton.ModalButton
                                onClick={open_archive_modal}
                                disabled={selectedSessions.length === 0}
                                colorClasses="text-green-600"
                                icon="archive" text="Archive"/>
                            <RLButton.ModalButton
                                onClick={() => setOpenDeleteModal(true)}
                                disabled={selectedSessions.length === 0}
                                colorClasses="text-red-600"
                                icon="trash" text="Delete"/>
                        </>
                    ) : null
                }
                <RLButton.ModalButton onClick={() => setOpen(false)}>{manageable ? 'Close' : 'Cancel'}</RLButton.ModalButton>
            </React.Fragment>
        }>
            {content}
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
