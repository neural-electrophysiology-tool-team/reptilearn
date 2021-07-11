import React from 'react';
import {Selector} from './components.js';
import ReactJson from 'react-json-view';
import {api_url} from './config.js';
import {ReflexContainer, ReflexSplitter, ReflexElement} from 'react-reflex';
import { BlocksView } from './blocks_view.js';
import { Dropdown, Modal, Button, Icon } from 'semantic-ui-react';

/*
  assign object o to object n without overwriting existing properties of o.
 */
/*
const assign_keep_old = (o, n) => {
    if (o === null || o === undefined)
        return n;
    if (n === null || n === undefined)
        return o;                        
    Object.keys(n).forEach(param => {
	if (o[param] !== undefined)
	    n[param] = o[param];
    });
    return n;
};
*/

export const ExperimentView = ({ctrl_state}) => {
    const [experimentList, setExperimentList] = React.useState([]);

    const [openNewSessionModal, setOpenNewSessionModal] = React.useState(false);
    const [selectedExperimentIdx, setSelectedExperimentIdx] = React.useState(0);
    
    const experiment_id_ref = React.useRef();
    
    const exp_url = api_url + "/experiment";

    const update_defaults = (override_blocks) => {
	/*
	fetch(exp_url + "/default_params")
	    .then(res => res.json())
	    .then(new_defaults => {
                if (new_defaults == null) {
                    setDefaultParams(null);
                    setDefaultBlocks(null);
                }
                else {                
                    const new_default_params = new_defaults.params === undefined ?
                          null : new_defaults.params;
                    const new_default_blocks = new_defaults.blocks === undefined ?
                          null : new_defaults.blocks;
                    
                    merge_params(new_default_params);
                    if (override_blocks ||
                        new_default_blocks.length === experimentBlocks.length ||
                        experimentBlocks.length === 0)
                        
                        merge_all_blocks(new_default_blocks);

                    setDefaultParams(new_default_params);
                    setDefaultBlocks(new_default_blocks);
                }
            });
	*/
    };

    /*
    const merge_params = (new_defaults) => {
        setExperimentParams(assign_keep_old(experimentParams, new_defaults));
    };

    const merge_all_blocks = (new_defaults) => {
        const blocks = [];
        new_defaults.forEach((new_block, i) => {
            blocks.push(merge_block(new_block, i));
        });
        setExperimentBlocks(blocks);
    };*/

    /*
    const merge_block = (new_defaults, block_idx) => {
        const new_default_block = {...new_defaults};
        const experiment_block = (experimentBlocks.length > block_idx) ?
              {...experimentBlocks[block_idx]} : null;

        return assign_keep_old(experiment_block, new_default_block);        
    };
    */
    
    const reset_params = () => {
        fetch(api_url + "/session/params/update", { method: "POST" });
    };

    const reset_all_blocks = () => {
        fetch(api_url + "/session/blocks/update", { method: "POST" });
    };

    const start_new_session = () => {
        setOpenNewSessionModal(false);
        const exp_name = experimentList[selectedExperimentIdx];
        
	fetch(api_url + "/session/start", {
	    method: "POST",
	    headers: {
		"Accept": "application/json",
		"Content-Type": "application/json"
	    },
	    body: JSON.stringify({
                "id": experiment_id_ref.current.value || exp_name,
                "experiment": exp_name
            })
	});
        
    };

    const run_experiment = () => {
        fetch(api_url + "/session/run");
    };

    const end_experiment = () => {
	fetch(api_url + "/session/end");
    };

    const on_params_changed = (e) => {
        fetch(api_url + "/session/params/update", {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(e.updated_src)
        });
    };

    const update_blocks = (blocks) => {
	fetch(api_url + "/session/blocks/update", {
	    method: "POST",
	    headers: {
		"Accept": "application/json",
		"Content-Type": "application/json"
            },
            body: JSON.stringify(blocks)
	});
    };

    const next_block = () => {
        fetch(api_url + "/session/next_block");
    };

    const next_trial = () => {
        fetch(api_url + "/session/next_trial");
    };
    
    if (!ctrl_state)
	return null;

    const session = ctrl_state.session;
    const is_running = ctrl_state.session ? ctrl_state.session.is_running : false;
    const cur_block = ctrl_state.session ? ctrl_state.session.cur_block : undefined;
    
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
    
    const session_menu = (
        <button className="title">
          <Dropdown text='Session'>
            <Dropdown.Menu>
              <Dropdown.Item text='Start new session...'
                             onClick={open_new_session_modal}
                             disabled={is_running}/>
              <Dropdown.Item text='Continue session...'
                             disabled={is_running}/>
            </Dropdown.Menu>
          </Dropdown>
        </button>
    );

    const new_session_modal = (
        <Modal
          onClose={() => setOpenNewSessionModal(false)}
          onOpen={() => setOpenNewSessionModal(true)}
          open={openNewSessionModal}
          size='mini'
        >
          <Modal.Header>Start a new session</Modal.Header>
          <Modal.Content>
            Experiment:
            <Selector options={experimentList}
                      selected={selectedExperimentIdx}
                      on_select={(exp, i) => setSelectedExperimentIdx(i)}/>
            <br/>
            Session id:
            <input type="text"
                   ref={experiment_id_ref}
                   placeholder={experimentList[selectedExperimentIdx]}
                   size="16"/>
          </Modal.Content>
          <Modal.Actions>
            <Button onClick={start_new_session} primary>Ok</Button>
            <Button onClick={() => setOpenNewSessionModal(false)}>Cancel</Button>
          </Modal.Actions>
        </Modal>
    );
    
    const exp_controls = (() => {
        if (!session)
            return null;

        const run_end_btn = is_running ?
          <button onClick={end_experiment}><Icon size="small" fitted name="stop"/></button>
	  : <button onClick={run_experiment}><Icon size="small" fitted name="play"/></button>;
        
        return (
            <React.Fragment>
              {run_end_btn}
            </React.Fragment>
        );
    })();
          
    const run_state_toolbar = !is_running ? null :
          <div className="subsection_header">
            <label>block:</label>
            <input type="text" readOnly value={ctrl_state.session.cur_block+1} size="3"/>
            <button onClick={next_block}>+</button>
            <label> trial:</label>
            <input type="text" readOnly value={ctrl_state.session.cur_trial+1} size="3"/>
            <button onClick={next_trial}>+</button>
          </div>;

    const params_height = is_running ? "calc(100% - 48px)" : "calc(100% - 20px)";
    
    const exp_interaction = ctrl_state.session ? (
        <div style={{overflow: "scroll", height: params_height}}>
          <div className="subsection_header">
            <span className="title">Parameters</span>
            <button onClick={reset_params} disabled={is_running}>Reset</button>
          </div>
          <div className="subsection">
	    <ReactJson src={ctrl_state.session.params}
		       name={null}
		       onEdit={is_running ? undefined : on_params_changed}
		       onAdd={is_running ? undefined : on_params_changed}
                       onDelete={is_running ? undefined : on_params_changed}
	    />
          </div>

          <div className="subsection_header">
            <span className="title">Blocks</span>
            <button onClick={reset_all_blocks} disabled={is_running}>Reset all</button>
          </div>
          <BlocksView is_running={is_running}
                      ctrl_state={ctrl_state}
                      set_blocks={update_blocks}
                      cur_block={cur_block}/>
        </div>        
    ) : null;
    
    return (
        <ReflexContainer orientation="horizontal">
          <ReflexElement minSize={26} style={{overflow: "hidden"}}>
            <div className="section_header">
              {session_menu}
              {new_session_modal}
              {exp_controls}
            </div>
            {run_state_toolbar}
            {exp_interaction}
          </ReflexElement>
          <ReflexSplitter/>
          <ReflexElement minSize={26} style={{overflow: "hidden"}}>
            <div className="section_header">
              <span className="title">State</span>
            </div>
            <div style={{overflow: "scroll", height: "calc(100% - 18px)"}}>
              <ReactJson src={ctrl_state}
                         name={null}
                         style={{height: "auto"}}
              />
            </div>
          </ReflexElement>        
        </ReflexContainer>
    );
};
