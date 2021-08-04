import React from 'react';
import { Modal, Button, Dropdown } from 'semantic-ui-react';
import { api_url } from './config.js';
import { Selector } from './components.js';

export const SessionStartView = ({ctrl_state, on_start}) => {
    const [experimentList, setExperimentList] = React.useState([]);
    const [open, setOpen] = React.useState(false);
    
    const experiment_id_ref = React.useRef();
    const experiment_selector_ref = React.useRef();

    const cur_exp_name = ctrl_state.experiment.cur_experiment;
    
    React.useEffect(() => {
	fetch(api_url + "/experiment/list")
	    .then(res => res.json())
            .then(
                (res) => {
                    setExperimentList(res);
                }
            );               
    }, []);

    const cur_exp_idx = cur_exp_name ? experimentList.indexOf(cur_exp_name) : null;
    const select_idx = cur_exp_idx!==null ? cur_exp_idx : experimentList.length + 1;
    
    const ok_click = () => {
        on_start("", "");
    };

    const dropdown_item = <Dropdown.Item
                            text='New session...'/>;
    
    return (
        <Modal
          trigger={dropdown_item}
          onClose={() => setOpen(false)}
          onOpen={() => setOpen(true)}
          open={open}
          size='mini'
        >
          <Modal.Header>Start a new session</Modal.Header>
          <Modal.Content>
            Experiment:
            <Selector options={experimentList}
                      selected={select_idx}
                      ref={experiment_selector_ref}
                      onClick={null}/>
            <br/>
            Session id:
            <input type="text"
                   ref={experiment_id_ref}
                   placeholder={cur_exp_name}
                   size="16"/>
            
          </Modal.Content>
          <Modal.Actions>
            <Button onClick={ok_click}
                    primary>
              Ok
            </Button>
            
            <Button onClick={() => setOpen(false)}>
              Cancel
            </Button>
          </Modal.Actions>
        </Modal>        
                   );
                   };
                       
