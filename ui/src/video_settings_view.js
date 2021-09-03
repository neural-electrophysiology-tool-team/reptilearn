import React from 'react';
import {api_url } from './config.js';
import { Modal, Button, Icon, Tab } from 'semantic-ui-react';
import ReactJson from 'react-json-view';

export const VideoSettingsView = ({ctrl_state, setOpen, open}) => {
    const [activeTabIdx, setActiveTabIdx] = React.useState(0);
    const [dirty, setDirty] = React.useState(false);
    
    if (!ctrl_state) {
        return null;
    }

    const apply = () => {
        setOpen(false);
    };
    
    const add_source = () => {
    };

    const on_conf_changed = (e) => {
        setDirty(true);
    };
    
    const panes = [
        { menuItem: 'Sources', render: () => (
            <Tab.Pane>
              <ReactJson src={ctrl_state.video.image_sources}
                         name={null}
                         onEdit={on_conf_changed}
                         onAdd={on_conf_changed}
                         onDelete={on_conf_changed}/>
            </Tab.Pane>
        ) },
        { menuItem: 'Observers', render: () => (
            <Tab.Pane>
              <ReactJson src={ctrl_state.video.image_observers}
                         name={null}
                         onEdit={on_conf_changed}
                         onAdd={on_conf_changed}
                         onDelete={on_conf_changed}/>

            </Tab.Pane>
        )}
    ];    
    
    return (
        <Modal
          onClose={() => setOpen(false)}
          onOpen={() => setOpen(true)}
          open={open}
          size='tiny'>
          <Modal.Header>Video settings</Modal.Header>
          <Modal.Content scrolling>
            <Tab menu={{ fluid: true }} panes={panes} activeInde={activeTabIdx}
                 onTabChange={(e, { activeIndex }) => setActiveTabIdx(activeIndex)}/>
          </Modal.Content>
          <Modal.Actions>
            <Button onClick={add_source}><Icon size="small" fitten name="add"/></Button>
            <Button onClick={() => setOpen(false)}>{dirty ? "Cancel" : "Close"}</Button>
        {dirty ? <Button onClick={apply}>Apply</Button> : null}
          </Modal.Actions>
        </Modal>
    );
        
};
