import React from 'react';
import {Selector} from './components.js';
import ReactJson from 'react-json-view';
import {api_url} from './config.js';
import {ReflexContainer, ReflexSplitter, ReflexElement} from 'react-reflex';
import { BlocksView } from './blocks_view.js';
import { Input, Dropdown, Modal, Button, Icon } from 'semantic-ui-react';
import { ActionsView } from './actions_view.js';
import { SessionListView } from './session_list_view.js';
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
    const [ctrlStatePath, setCtrlStatePath] = React.useState();
    
    const [openNewSessionModal, setOpenNewSessionModal] = React.useState(false);
    const [openDeleteModal, setOpenDeleteModal] = React.useState(false);
    const [openSessionListModal, setOpenSessionListModal] = React.useState(false);
    
    const [selectedExperimentIdx, setSelectedExperimentIdx] = React.useState(0);
    const [experimentIdInput, setExperimentIdInput] = React.useState('');
    
    const path_input_ref = React.useRef();
    
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

    const delete_session = () => {
        setOpenDeleteModal(false);
        fetch(api_url + "/session/delete");
    };
    
    const run_experiment = () => {
        fetch(api_url + "/session/run");
    };

    const stop_experiment = () => {
	fetch(api_url + "/session/stop");
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

    const reset_phase = () => {
	fetch(api_url + "/session/reset_phase");
    };

    const update_ctrl_state_path = () => {
        if (!path_input_ref.current) {
            setCtrlStatePath(ctrl_state);
            return;
        }
        
        const path = path_input_ref.current.value;
        if (path.trim().length === 0) {
            setCtrlStatePath(ctrl_state);
            return;
        }
        
        const path_terms = path.split('.');

        let cur = ctrl_state;
        for (const term of path_terms) {
            if (cur[term]) {
                cur = cur[term];
            }
            else {
                setCtrlStatePath({});
                return;
            }
        }

        setCtrlStatePath(cur);
    };

    React.useEffect(update_ctrl_state_path, [ctrl_state]);
    
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

    const open_session_list_modal = () => {
	setOpenSessionListModal(true);
    };
    
    const session_title = session ? `Session ${session.id}` : "Session";

    const session_menu = (
          <button className="title">
            <Dropdown text={session_title}>
              <Dropdown.Menu>
                <Dropdown.Item text='Start new session...'
                               onClick={open_new_session_modal}
                               disabled={is_running}/>
                <Dropdown.Item text='Continue session...'
                               disabled={is_running}
			       onClick={open_session_list_modal}/>
                <Dropdown.Divider/>
                <Dropdown.Item text='Close session'
                               disabled={!session || is_running}
                               onClick={close_session}/>
                
                <Dropdown.Item text='Delete session...'
                               onClick={() => setOpenDeleteModal(true)}
                               disabled={!session || is_running}/>
                
              </Dropdown.Menu>
            </Dropdown>
        </button>
    );

    const delete_session_modal = session ? (
        <Modal size="small"
               onClose={() => setOpenDeleteModal(false)}
               onOpen={() => setOpenDeleteModal(true)}
               open={openDeleteModal}>
          <Modal.Header>Are you sure?</Modal.Header>
          <Modal.Content>
            <p>This will delete data directory:</p>
            <p>{session.data_dir}</p>
          </Modal.Content>
          <Modal.Actions>
            <Button onClick={delete_session} negative>Yes</Button>
            <Button onClick={() => setOpenDeleteModal(false)} positive>No</Button>
          </Modal.Actions>
        </Modal>
    ) : null;

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

    const session_list_modal = (
        <SessionListView onSelect={session_name => continue_session(session_name)}
                         open={openSessionListModal}
                         setOpen={setOpenSessionListModal}/>
    );

    const exp_controls = (() => {
        if (!session)
            return null;

        const run_end_btn = is_running ?
          <button onClick={stop_experiment}><Icon size="small" fitted name="stop"/></button>
	  : <button onClick={run_experiment}><Icon size="small" fitted name="play"/></button>;
        
        const actions_view = ctrl_state.session.actions && ctrl_state.session.actions.length > 0 ?
              <ActionsView actions={ctrl_state.session.actions}/>
              : null;
              
        
        return(
            <React.Fragment>
              {run_end_btn}
              {actions_view}
            </React.Fragment>
        );
    })();

    const phase_toolbar = !session ? null :
          <div className="subsection_header">
            <label>block:</label>
            <input type="text" readOnly value={session.cur_block+1} size="3"/>
            <button onClick={next_block}>+</button>
            <label> trial:</label>
            <input type="text" readOnly value={session.cur_trial+1} size="3"/>
            <button onClick={next_trial}>+</button>
            <button onClick={reset_phase}><Icon size="small" fitted name="undo"/></button>
          </div>;

    const params_height = session ? "calc(100% - 48px)" : "calc(100% - 20px)";
    
    const exp_interaction = session ? (
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
                      params={ctrl_state.session.params}
                      blocks={ctrl_state.session.blocks}
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
	      {delete_session_modal}
	      {session_list_modal}
              {exp_controls}
            </div>
            {phase_toolbar}
            {exp_interaction}
          </ReflexElement>
          <ReflexSplitter/>
          <ReflexElement minSize={26} style={{overflow: "hidden"}}>
            <div className="section_header">
              <span className="title">State</span>
              <input type="search"
                     placeholder="path"
                     ref={path_input_ref}
                     onChange={update_ctrl_state_path}/>
            </div>
            <div style={{overflow: "scroll", height: "calc(100% - 18px)"}}>
              <ReactJson src={ctrlStatePath}
                         name={null}
                         style={{height: "auto"}}
              />
            </div>
          </ReflexElement>        
        </ReflexContainer>
    );
};
