import React from 'react';
import { api_url } from './config.js';
import { Modal, Table, Button, Icon, Checkbox } from 'semantic-ui-react';
import { ArchiveView } from './archive_view.js';
import { DeleteSessionModal } from './delete_session_modal.js';

export const SessionListView = ({onSelect, setOpen, open, selectable, manageable}) => {
    const [sessionList, setSessionList] = React.useState(null);
    const [selectedSessions, setSelectedSessions] = React.useState([]);
    const [openArchiveModal, setOpenArchiveModal] = React.useState(false);
    const [openDeleteModal, setOpenDeleteModal] = React.useState(false);

    React.useEffect(() => {
        setSelectedSessions([]);
        fetch(api_url + "/session/list")
	    .then(res => res.json())
	    .then((res) => {
                setSessionList(res);
            });
    }, [open]);

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
	    <Table.Row key={s}>
              { manageable ? (
                <Table.Cell collapsing>
                  <Checkbox onChange={() => toggle_session(s)}/>
                </Table.Cell>
              ) : null }
              <Table.Cell>
                {selectable ?
                 <a href="#" onClick={() => onSelect(s[2])}>{s[0]}</a>
                 : s[0]
                }
              </Table.Cell>
              <Table.Cell>
                {s[1]}
              </Table.Cell>
              <Table.Cell>
                <Button.Group icon compact>
                </Button.Group>
              </Table.Cell>
            </Table.Row>
        );
    }).reverse() : undefined;

    const content = items ? (
        <Table compact celled>
          {items}
        </Table>
    ) : "Loading...";
    
    return (
        <React.Fragment>
          <Modal
            onClose={() => setOpen(false)}
            onOpen={() => setOpen(true)}
            open={open}
            size='small' >
            <Modal.Header>{selectable ? 'Select session' : 'Sessions'}</Modal.Header>
            <Modal.Content scrolling>
              {content}
            </Modal.Content>
            <Modal.Actions>
              {
                  manageable ? (
                      <React.Fragment>
                        <Button icon title="Archive" positive
                                onClick={open_archive_modal}
                                disabled={selectedSessions.length === 0}>
                          <Icon name="archive"/>Archive
                        </Button>
                        <Button icon title="Delete" negative
                                onClick={() => setOpenDeleteModal(true)}
                                disabled={selectedSessions.length === 0}><Icon name="delete"/>Delete</Button>
                      </React.Fragment>
                  ) : null
              }
	      <Button onClick={() => setOpen(false)}>{manageable ? 'Close' : 'Cancel'}</Button>
            </Modal.Actions>
          </Modal>
          <ArchiveView sessions={selectedSessions}
                       setOpen={setOpenArchiveModal}
                       close_session_list={() => setOpen(false)}
                       open={openArchiveModal}/>
          <DeleteSessionModal sessions={selectedSessions}
                              setOpen={setOpenDeleteModal}
                              close_session_list={() => setOpen(false)}
                              open={openDeleteModal}/>
        </React.Fragment>
     );
};
