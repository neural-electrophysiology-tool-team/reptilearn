import React from 'react';
import { useSelector } from 'react-redux';

import { SessionListView } from './session_list_view.js';
import { DeleteSessionModal } from './delete_session_view.js';
import RLMenu from './ui/menu.js';
import RLModal from './ui/modal.js';
import { RLListbox, RLSimpleListbox } from './ui/list_box.js';
import RLButton from './ui/button.js';
import RLInput from './ui/input.js';
import { api } from '../api.js';

export const SessionMenuView = () => {
    const ctrl_state = useSelector((state) => state.reptilearn.ctrlState);
    const [experimentList, setExperimentList] = React.useState([]);
    const [openNewSessionModal, setOpenNewSessionModal] = React.useState(false);
    const [openDeleteModal, setOpenDeleteModal] = React.useState(false);
    const [openSessionListModal, setOpenSessionListModal] = React.useState(false);
    const [manageSessions, setManageSessions] = React.useState(false);

    const [selectedExperiment, setSelectedExperiment] = React.useState(null);
    const [experimentIdInput, setExperimentIdInput] = React.useState('');

    const open_new_session_modal = () => {
        api.experiment.get_list()
            .then(
                (res) => {
                    setExperimentList(res);
                    setSelectedExperiment(res[0])
                }
            )
            .then(() => setOpenNewSessionModal(true));
    };

    const open_session_list_modal = (manage_sessions) => {
        setManageSessions(manage_sessions);
        setOpenSessionListModal(true);
    };

    const create_session = () => {
        setOpenNewSessionModal(false);
        api.session.create(experimentIdInput || selectedExperiment, selectedExperiment);
    };

    const continue_session = (session_name) => {
        setOpenSessionListModal(false);
        api.session.continue(session_name);
    };

    if (!ctrl_state)
        return null;

    const session = ctrl_state.session;

    const reload_session = () => {
        const split_dir = session.data_dir.split('/');
        return api.session.continue(split_dir[split_dir.length - 1]);
    };

    const is_running = ctrl_state.session ? ctrl_state.session.is_running : false;
    const is_recording = !!ctrl_state.video?.record?.is_recording;

    const new_session_modal = (
        <RLModal open={openNewSessionModal} setOpen={setOpenNewSessionModal} sizeClasses="h-fit" header="Start a new session"
            actions={
                <React.Fragment>
                    <RLButton.ModalButton onClick={create_session}>Ok</RLButton.ModalButton>
                    <RLButton.ModalButton onClick={() => setOpenNewSessionModal(false)}>Cancel</RLButton.ModalButton>
                </React.Fragment>
            }>
            <table className="border-separate [border-spacing:0.75rem]">
                <tbody>
                    <tr>
                        <td>Experiment:</td>
                        <td>
                            {experimentList.length > 0
                                ? (
                                    <RLSimpleListbox
                                        options={RLListbox.valueOnlyOptions(experimentList)}
                                        selected={selectedExperiment}
                                        setSelected={setSelectedExperiment}
                                        className="w-full" />
                                ) : <div>Loading...</div>}
                        </td>
                    </tr>
                    <tr>
                        <td>Session id:</td>
                        <td>
                            <RLInput.Text
                                value={experimentIdInput}
                                onChange={(e) => setExperimentIdInput(e.target.value)}
                                placeholder={selectedExperiment}
                                className="w-full"
                                autoFocus />
                        </td>
                    </tr>
                </tbody>
            </table>
        </RLModal>
    );

    return (
        <React.Fragment>
            <DeleteSessionModal session={session} open={openDeleteModal} setOpen={setOpenDeleteModal} />
            <SessionListView onSelect={session_name => continue_session(session_name)}
                selectable={!manageSessions}
                manageable={manageSessions}
                open={openSessionListModal}
                setOpen={setOpenSessionListModal} />
            {new_session_modal}
            <RLMenu button={<RLMenu.TopBarMenuButton title="Session" />}>
                <RLMenu.ButtonItem
                    onClick={open_new_session_modal}
                    disabled={!!session}>Start new session...</RLMenu.ButtonItem>
                <RLMenu.ButtonItem
                    onClick={() => open_session_list_modal(false)}
                    disabled={!!session}>Continue session...</RLMenu.ButtonItem>
                <RLMenu.ButtonItem
                    disabled={!!session}
                    onClick={() => open_session_list_modal(true)}>Manage sessions...</RLMenu.ButtonItem>

                <RLMenu.SeparatorItem />

                <RLMenu.ButtonItem
                    disabled={!session || is_running || is_recording}
                    onClick={api.session.close}>Close session</RLMenu.ButtonItem>
                <RLMenu.ButtonItem
                    disabled={!session || is_running || is_recording}
                    onClick={reload_session}>Reload session</RLMenu.ButtonItem>
                <RLMenu.ButtonItem
                    onClick={() => setOpenDeleteModal(true)}
                    disabled={!session || is_running || is_recording}>Delete session...</RLMenu.ButtonItem>
            </RLMenu>
        </React.Fragment>
    );
};
