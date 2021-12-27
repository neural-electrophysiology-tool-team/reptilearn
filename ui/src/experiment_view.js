import React from 'react';
import ReactJson from 'react-json-view';
import { api_url } from './config.js';
import { ReflexContainer, ReflexSplitter, ReflexElement } from 'react-reflex';
import { BlocksView } from './blocks_view.js';
import { Icon, Dropdown } from 'semantic-ui-react';
import { ActionsView } from './actions_view.js';

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
    const [ctrlStatePath, setCtrlStatePath] = React.useState();
    const [statePath, setStatePath] = React.useState([]);
    
    /*
    const update_defaults = (override_blocks) => {
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
    };
    */
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
        if (!statePath || statePath.length === 0) {
            setCtrlStatePath(ctrl_state);
            return;
        }
        
        //

        let cur = ctrl_state;
        for (const key of statePath) {
            if (cur[key]) {
                cur = cur[key];
            }
            else {
                setCtrlStatePath({});
                return;
            }
        }

        setCtrlStatePath(cur);
    };

    const keys_for_path = (i) => {
        let cur = ctrl_state;
        for (const key of statePath) {
            if (i === 0)
                break;
            
            if (cur[key]) {
                cur = cur[key];
                i--;
            }
            else {
                return [];
            }
        }

        return Object.keys(cur)
            .filter(k => cur[k] instanceof Array || cur[k] instanceof Object);
    };
    
    React.useEffect(update_ctrl_state_path, [ctrl_state, statePath]);
    
    if (!ctrl_state)
	return null;
    
    const is_running = ctrl_state.session ? ctrl_state.session.is_running : false;
    const cur_block = ctrl_state.session ? ctrl_state.session.cur_block : undefined;
    const session = ctrl_state.session;

    const session_title = (() => {
        if (!session) return "Session";
        
        const st = new Date(session.start_time);
        const start_time_format = st.getDate()  + "-" + (st.getMonth()+1) + "-" + st.getFullYear() + " " +
              st.getHours() + ":" + st.getMinutes();
        return `Session ${session.id} (${ctrl_state.session.experiment} ${start_time_format})`;
    })();
    
    
    const run_end_btn = session ? (is_running ? (
        <button onClick={stop_experiment}><Icon size="small" fitted name="stop"/></button>)
	: <button onClick={run_experiment}><Icon size="small" fitted name="play"/></button>)
          : null;

    const actions_view = session && session.actions && session.actions.length > 0 ?
          <button><ActionsView actions={ctrl_state.session.actions}/></button>
          : null;
    
    const phase_toolbar = !session ? null :
          <div className="subsection_header">
            {run_end_btn}
            <label>block:</label>
            <input type="text" readOnly value={session.cur_block+1} size="3"/>
            <button onClick={next_block}>+</button>
            <label> trial:</label>
            <input type="text" readOnly value={session.cur_trial+1} size="3"/>
            <button onClick={next_trial}>+</button>
            <button onClick={reset_phase}><Icon size="small" fitted name="undo"/></button>
            {actions_view}
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

    const state_path_select = (i) => {
        const on_change = (e, { value }) => {
            const state_path = [...statePath];

            if (!value) {
                setStatePath(statePath.slice(0, i));
                return;
            }
            
            state_path[i] = value;
            setStatePath(state_path);
        };

        const opts = keys_for_path(i).map(k => ({
            key: k, text: k, value: k
        }));

        if (opts.length === 0)
            return null;
        
        return (
            <Dropdown placeholder="..."
                      className="tiny"
                      selection
                      clearable
                      compact
		      key={i}
                      options={opts}
                      value={statePath[i]}
                      onChange={on_change}/>
        );
    };
    
    return (
        <ReflexContainer orientation="horizontal" className="controls-view">
          <ReflexElement minSize={26} style={{overflow: "hidden"}}>
            <div className="section_header">
              <span className="title">{session_title}</span>
            </div>
            {phase_toolbar}
            {exp_interaction}
          </ReflexElement>
          <ReflexSplitter/>
          <ReflexElement minSize={26} style={{overflow: "hidden"}}>
            <div className="section_header">
              <span className="title">State</span>
              {[...statePath.map((p, idx) => state_path_select(idx)),
                state_path_select(statePath.length)
               ]}
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
