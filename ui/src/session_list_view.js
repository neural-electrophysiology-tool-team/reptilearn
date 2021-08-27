import React from 'react';
import { api_url } from './config.js';
import { Modal, List, Button } from 'semantic-ui-react';

export const SessionListView = ({onSelect, setOpen, open}) => {
    const [sessionList, setSessionList] = React.useState(null);

    React.useEffect(() => {
        fetch(api_url + "/session/list")
	    .then(res => res.json())
	    .then((res) => {
                setSessionList(res);
            });
    }, [open]);

    const items = sessionList ? sessionList.map(s => {
        return (
	    <List.Item key={s}>
              <List.Content>
                <List.Header>
                      <a onClick={() => onSelect(s[2])} href="#">{s[0]}</a>
                </List.Header>
                <List.Description>
                  {s[1]}
                </List.Description>
              </List.Content>
            </List.Item>
        );
    }).reverse() : undefined;

    const content = items ? (
        <List relaxed divided>
          {items}
        </List>
    ) : "Loading...";
    
    return (
        <Modal
          onClose={() => setOpen(false)}
          onOpen={() => setOpen(true)}
          open={open}
          size='tiny' >
          <Modal.Header>Select session</Modal.Header>
          <Modal.Content scrolling>
            {content}
          </Modal.Content>
          <Modal.Actions>
	    <Button onClick={() => setOpen(false)}>Cancel</Button>
          </Modal.Actions>
        </Modal>
     );
};
