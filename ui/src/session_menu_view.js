import React from 'react';
import { Dropdown, Button, Modal, Input } from 'semantic-ui-react';
import { api_url } from './config.js';

import { SessionListView } from './session_list_view.js';
import { DeleteSessionModal } from './delete_session_modal.js';

export const SessionMenuView = ({ctrl_state}) => {
    const [experimentList, setExperimentList] = React.useState([]);
    const [openNewSessionModal, setOpenNewSessionModal] = React.useState(false);
    const [openDeleteModal, setOpenDeleteModal] = React.useState(false);
    const [openSessionListModal, setOpenSessionListModal] = React.useState(false);
    const [manageSessions, setManageSessions] = React.useState(false);
    
    const [selectedExperimentIdx, setSelectedExperimentIdx] = React.useState(0);
    const [experimentIdInput, setExperimentIdInput] = React.useState('');
    
    const open_new_session_modal = () => {
	fetch(api_url + "/experiment/list")
	    .then(res => res.json())
            .then(
                (res) => {
                    setExperimentList(res);
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
        const exp_name = experimentList[selectedExperimentIdx];
        
	fetch(api_url + "/session/create", {
	    method: "POST",
	    headers: {
		"Accept": "application/json",
		"Content-Type": "application/json"
	    },
	    body: JSON.stringify({
                "id": experimentIdInput || exp_name,
                "experiment": exp_name
            })
	});
        
    };
    
    const continue_session = (session_name) => {
        setOpenSessionListModal(false);
        fetch(api_url + "/session/continue/" + session_name);
    };
    
    const close_session = () => {
        fetch(api_url + "/session/close");
    };

    if (!ctrl_state)
	return null;
    
    const session = ctrl_state.session;
    
    const reload_session = () => {
        fetch(api_url + "/session/close")
            .then(() => {
                const split_dir = session.data_dir.split('/');
                return fetch(api_url + "/session/continue/" + split_dir[split_dir.length-1]);
            });
    };        
    
    const is_running = ctrl_state.session ? ctrl_state.session.is_running : false;
    const is_recording = !!ctrl_state.video?.record?.is_recording;
    
    const experiment_options = experimentList.map((e, i) => {return {text: e, key: e, value: i};});
    const new_session_modal = (
        <Modal
          onClose={() => setOpenNewSessionModal(false)}
          onOpen={() => setOpenNewSessionModal(true)}
          open={openNewSessionModal}
          size='mini'
        >
          <Modal.Header>Start a new session</Modal.Header>
          <Modal.Content>
            <table>
              <tbody className="full-width">
                <tr>
                  <th>Experiment:</th>
                  <td>
                    <Dropdown options={experiment_options}
                              selection
                              defaultValue={experiment_options.length > 0 ? experiment_options[selectedExperimentIdx].value : null}
                              onChange={(e, opt) => setSelectedExperimentIdx(opt.value)}
                              className="full-width"/> 
                  </td>
                </tr>
                <tr>
                  <th>Session id:</th>
                  <td>
                    <Input type="text"
                           value={experimentIdInput}
                           onChange={(e, data) => setExperimentIdInput(data.value)}
                           placeholder={experimentList[selectedExperimentIdx]}
                           className="full-width"
                           autoFocus/>
                  </td>
                </tr>                
              </tbody>
            </table>

            <br/>            
          </Modal.Content>
          <Modal.Actions>
            <Button onClick={create_session} primary>Ok</Button>
            <Button onClick={() => setOpenNewSessionModal(false)}>Cancel</Button>
          </Modal.Actions>
        </Modal>
    );

    return (
        <React.Fragment>
          <DeleteSessionModal session={session} open={openDeleteModal} setOpen={setOpenDeleteModal}/>
          <SessionListView onSelect={session_name => continue_session(session_name)}
                           selectable={!manageSessions}
                           manageable={manageSessions}
                           open={openSessionListModal}
                           setOpen={setOpenSessionListModal}/>
          {new_session_modal}
          <Dropdown item text="Session">
            <Dropdown.Menu>
              <Dropdown.Item text='Start new session...'
                             onClick={open_new_session_modal}
                             disabled={!!session}/>
              <Dropdown.Item text='Continue session...'
                             disabled={!!session}
			     onClick={() => open_session_list_modal(false)}/>
              <Dropdown.Item text='Manage sessions...'
                             disabled={!!session}
                             onClick={() => open_session_list_modal(true)}/>
              <Dropdown.Divider/>
              <Dropdown.Item text='Close session'
                             disabled={!session || is_running || is_recording}
                             onClick={close_session}/>
              <Dropdown.Item text='Reload session'
                             disabled={!session || is_running || is_recording}
                             onClick={reload_session}/>
              <Dropdown.Item text='Delete session...'
                             onClick={() => setOpenDeleteModal(true)}
                             disabled={!session || is_running || is_recording}/>
              
            </Dropdown.Menu>
          </Dropdown>          
        </React.Fragment>
    );
};
