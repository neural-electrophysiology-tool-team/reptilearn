import React from 'react';
import {Selector} from './components.js';
import ReactJson from 'react-json-view'

export const ExperimentView = ({ctrl_state}) => {
    const [experimentList, setExperimentList] = React.useState([]);
    const [experimentParams, setExperimentParams] = React.useState({});
    const [error, setError] = React.useState(null);
    
    React.useEffect(() => {
	fetch("http://localhost:5000/list_experiments")
	    .then(res => res.json())
            .then(
                (res) => {
                    setExperimentList(res);
                },
                (error) => {
                    setError(error.toString());
                }
            );               
    }, []);

    const set_experiment = val => {
	fetch(`http://localhost:5000/set_experiment/${val}`)
    };

    const run_experiment = () => {
	fetch("http://localhost:5000/run_experiment", {
	    method: "POST",
	    headers: {
		"Accept": "application/json",
		"Content-Type": "application/json"
	    },
	    body: JSON.stringify(experimentParams)
	}).then(res => {
	    if (!res.ok)
		res.text().then(json => console.log(json))
	});
	
    };

    const end_experiment = () => {
	fetch("http://localhost:5000/end_experiment")
	    .then(res => console.log(res));
    };

    const on_params_changed = (e) => {
	setExperimentParams(e.updated_src);
    };

    if (!ctrl_state)
	return null;

    const cur_exp_name = ctrl_state.experiment.cur_experiment;
    const cur_exp_idx = experimentList.indexOf(cur_exp_name) + 1;
    const is_running = ctrl_state.experiment.is_running;
    
    console.log(cur_exp_name);
    const reload_btn = cur_exp_name ?
	<button onClick={(e) => set_experiment(cur_exp_name)}
		disabled={is_running}>
	    Reload
	</button> :
	  null;
    
    const run_end_btn = is_running ?
        <button onClick={end_experiment}>End Experiment</button>
	  :
          <button onClick={run_experiment}>Run Experiment</button>;
    
    return (
	<div className="component">
          Experiment:
	    <Selector options={["None"].concat(experimentList)}
		      selected={cur_exp_idx}
		      on_select={set_experiment}
	              disabled={ctrl_state.experiment.is_running}/>
	    {reload_btn}
	    <br/>
	    <label>Parameters:</label>
	    <ReactJson src={experimentParams}
		       name={null}
		       onEdit={on_params_changed}
		       onAdd={on_params_changed}
	    />
	    {run_end_btn}
	</div>
    );
};
