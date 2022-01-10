import React from 'react';
import { Modal, Button } from 'semantic-ui-react';
import { api_url } from './config.js';

export const DeleteSessionModal = ({ session, sessions, open, setOpen, close_session_list }) => {
    const [dataRoot, setDataRoot] = React.useState(null);
    
    React.useEffect(() => {
        fetch(api_url + "/config/session_data_root")
            .then((res) => res.json())
            .then((res) => setDataRoot(res));
    }, [open]);

    if (session) {
        const data_dir = session.data_dir.split('/');
        sessions = [['', '', data_dir[data_dir.length-1]]];
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
                setOpen(false);
                if (close_session_list) {
                    close_session_list();
                }
            });
    };

    return (
        <Modal size="small"
               onClose={() => setOpen(false)}
               onOpen={() => setOpen(true)}
               open={open}>
          <Modal.Header>Are you sure?</Modal.Header>
          <Modal.Content>
            <p>The following data directories will be deleted:</p>
            <ul>
              { sessions.map((s) => <li key='s'>{dataRoot + '/' + s[2]}</li>) }
            </ul>
          </Modal.Content>
          <Modal.Actions>
            <Button onClick={delete_sessions} negative>Yes</Button>
            <Button onClick={() => setOpen(false)} positive>No</Button>
          </Modal.Actions>
        </Modal>
    );    
};

