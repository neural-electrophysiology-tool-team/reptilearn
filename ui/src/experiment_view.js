import React from 'react';
import {Selector} from './components.js';
import ReactJson from 'react-json-view';
import {api_url} from './config.js';
import {ReflexContainer, ReflexSplitter, ReflexElement} from 'react-reflex';
import { BlocksView } from './blocks_view.js';

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

export const ExperimentView = ({ctrl_state}) => {
    const [experimentList, setExperimentList] = React.useState([]);
    const [experimentParams, setExperimentParams] = React.useState({});
    const [experimentBlocks, setExperimentBlocks] = React.useState([]);
    const [defaultParams, setDefaultParams] = React.useState(null);
    const [defaultBlocks, setDefaultBlocks] = React.useState(null);
    const experimentIdInput = React.useRef();
    
    const exp_url = api_url + "/experiment";

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

    const merge_params = (new_defaults) => {
        setExperimentParams(assign_keep_old(experimentParams, new_defaults));
    };

    const merge_all_blocks = (new_defaults) => {
        const blocks = [];
        new_defaults.forEach((new_block, i) => {
            blocks.push(merge_block(new_block, i));
        });
        setExperimentBlocks(blocks);
    };

    const merge_block = (new_defaults, block_idx) => {
        const new_default_block = {...new_defaults};
        const experiment_block = (experimentBlocks.length > block_idx) ?
              {...experimentBlocks[block_idx]} : null;

        return assign_keep_old(experiment_block, new_default_block);        
    };
    
    const reset_params = () => {
        setExperimentParams(defaultParams);
    };

    const reset_all_blocks = () => {
        setExperimentBlocks(defaultBlocks);
    };
    
    const set_experiment = (exp_name, override_blocks) => {
        if (is_running) {
            update_defaults(false);
            return;
        }

        const new_exp = override_blocks|| exp_name !== ctrl_state.experiment.cur_experiment;
	if (new_exp) {
	    setExperimentParams({});
            setExperimentBlocks([{}]);
	}

	fetch(exp_url + `/set/${exp_name}`)
	    .then((res) => {
                update_defaults(new_exp);
            });
    };

    const refresh_experiment_list = () => {
        fetch(exp_url + "/refresh_list")
            .then(res => res.json())
            .then(res => setExperimentList(res));
    };

    const select_experiment = (opt, idx) => {
        if (idx >= experimentList.length) {
            if (opt === "None")
                set_experiment("None");
            else
                refresh_experiment_list();
        }
        else {
            set_experiment(opt);
        }
    };
    
    const run_experiment = () => {
        const id = experimentIdInput.current.value.trim() === "" ?
              cur_exp_name : experimentIdInput.current.value;
        
	fetch(exp_url + "/run", {
	    method: "POST",
	    headers: {
		"Accept": "application/json",
		"Content-Type": "application/json"
	    },
	    body: JSON.stringify({
                "id": id,
                "params": experimentParams,
		"blocks": experimentBlocks})
	});
	
    };

    const end_experiment = () => {
	fetch(exp_url + "/end")
	    .then(res => console.log(res));
    };

    const on_params_changed = (e) => {
	setExperimentParams(e.updated_src);
    };

    const next_block = () => {
        fetch(exp_url + "/next_block");
    };

    const next_trial = () => {
        fetch(exp_url + "/next_trial");
    };

    React.useEffect(() => {
	fetch(exp_url + "/list")
	    .then(res => res.json())
            .then(
                (res) => {
                    setExperimentList(res);
                    if (ctrl_state != null && ctrl_state.experiment.cur_experiment != null) {
                        set_experiment(ctrl_state.experiment.cur_experiment, true);
                    }                    
                }
            );               
    }, []);

    
    if (!ctrl_state)
	return null;

    const cur_exp_name = ctrl_state.experiment.cur_experiment;
    const cur_exp_idx = cur_exp_name ? experimentList.indexOf(cur_exp_name) : null;
    const is_running = ctrl_state.experiment.is_running;

    const experiment_selector = (() => {
        const sep = "\u2500\u2500\u2500\u2500\u2500";
        const select_idx = cur_exp_idx!==null ? cur_exp_idx : experimentList.length + 1;
        return <Selector
                 options={experimentList.concat([sep, "None", "Refresh list"])}
		 selected={select_idx}
		 on_select={select_experiment}
                 disabled_options={[sep]}
	         disabled={ctrl_state.experiment.is_running}
               />;
    })();
    
    const run_end_btn = is_running ?
          <button onClick={end_experiment}>End</button>
	  : <button onClick={run_experiment}>Run</button>;

    const exp_controls = cur_exp_name ? (
        <React.Fragment>
          <button onClick={(e) => set_experiment(cur_exp_name)}
		  disabled={is_running}>
	    Reload
	  </button>
          id:
          <input type="text"
                 ref={experimentIdInput}
                 placeholder={cur_exp_name}
                 disabled={is_running}
                 size="16"/>
          {run_end_btn}
        </React.Fragment>
    ) : null;
          

    const run_state_element = !is_running ? null :
          <div className="subsection_header">
            <label>block:</label>
            <input type="text" readOnly value={ctrl_state.experiment.cur_block+1} size="3"/>
            <button onClick={next_block}>+</button>
            <label> trial:</label>
            <input type="text" readOnly value={ctrl_state.experiment.cur_trial+1} size="3"/>
            <button onClick={next_trial}>+</button>
          </div>;

    const params_div = experimentParams !== null ?
          (
              <React.Fragment>
                <div className="subsection_header">
                  <span className="title">Parameters</span>
                  <button onClick={reset_params} disabled={is_running}>Reset</button>
                </div>
                <div className="subsection">
	          <ReactJson src={experimentParams}
		             name={null}
		             onEdit={on_params_changed}
		             onAdd={on_params_changed}
                             onDelete={on_params_changed}
	          />
                </div>
              </React.Fragment>

          ) : null;

    const params_height = is_running ? "calc(100% - 48px)" : "calc(100% - 20px)";
    
    return (
        <ReflexContainer orientation="horizontal">
          <ReflexElement minSize={26} style={{overflow: "hidden"}}>
            <div className="section_header">
              <span className="title">Experiment</span>
              {experiment_selector}
              {exp_controls}
            </div>
            {run_state_element}
            <div style={{overflow: "scroll", height: params_height}}>
              {params_div}
              <div className="subsection_header">
                <span className="title">Blocks</span>
                <button onClick={reset_all_blocks} disabled={is_running}>Reset all</button>
              </div>
              <BlocksView is_running={is_running}
                          params={experimentParams}
                          blocks={experimentBlocks}
                          default_blocks={defaultBlocks}
                          set_blocks={setExperimentBlocks}
                          cur_block={ctrl_state.experiment.cur_block}/>
            </div>            
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
