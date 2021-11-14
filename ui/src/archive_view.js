import React from 'react';
import { api_url } from './config.js';
import { Modal, Button, Dropdown } from 'semantic-ui-react';

export const ArchiveView = ({sessions, setOpen, open, close_session_list}) => {
    const [archives, setArchives] = React.useState(null);
    const [selection, setSelection] = React.useState([]);
    
    React.useEffect(() => {
        fetch(api_url + "/config/archive_dirs")
	    .then((res) => res.json())
	    .then((res) => setArchives(res));
    }, [open]);

    const archive_option = (e) => {
        return {
            key: e[0],
            value: e[0],
            text: e[0]
        };
    };

    const selection_changed = (e, { value }) => {
        setSelection(value);
    };

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
            })})
            .then(() => {
                setOpen(false);
                if (close_session_list) {
                    close_session_list();
                }
            });       
    };

    const archive_options = archives ? Object.entries(archives).map(archive_option) : null;
    
    return (
        <Modal
          onClose={() => setOpen(false)}
          onOpen={() => setOpen(true)}
          open={open}
          size='tiny'>
          <Modal.Header>Archive {sessions.length} sessions</Modal.Header>
          <Modal.Content>
            <Dropdown selection multiple placeholder='Select destination(s)'
                      options={archive_options} loading={archives === null}
                      onChange={selection_changed}
                      value={selection}/>
          </Modal.Content>
          <Modal.Actions>
            <Button primary onClick={copy} disabled={selection.length === 0}>Copy</Button>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
          </Modal.Actions>
        </Modal>
    );
};
