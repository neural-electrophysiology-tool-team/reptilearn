import React from 'react';
import {Selector} from './components.js';
import ReactJson from 'react-json-view'

export const ExperimentView = ({cur_experiment}) => {
    const [experimentList, setExperimentList] = React.useState([]);
    const [experimentParams, setExperimentParams] = React.useState({});
    const [error, setError] = React.useState(null);
    
    React.useEffect(() => {
	fetch("http://localhost:5000/list_experiments")
	    .then(res => res.json())
            .then(
                (res) => {
                    setExperimentList(res);
		    if (res.length > 0)
			set_experiment(res[0]);
                },
                (error) => {
                    setError(error.toString());
                }
            );               
    }, []);

    const set_experiment = (val, idx) => {
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
		res.json().then(json => console.log(json))
	});
	
    }

    const end_experiment = () => {
	fetch("http://localhost:5000/end_experiment")
	    .then(res => console.log(res));
    }

    const on_params_changed = (e) => {
	setExperimentParams(e.updated_src);
    }

    const cur_exp_idx = experimentList.indexOf(cur_experiment) + 1
	
    return (
	<div className="component">
          Experiment:
	    <Selector options={["None"].concat(experimentList)}
		      selected={cur_exp_idx}
		      on_select={set_experiment} /><br/>
	    <label>Parameters:</label>
	    <ReactJson src={experimentParams}
		       name={null}
		       onEdit={on_params_changed}
		       onAdd={on_params_changed}
	    />
	    <button onClick={run_experiment}>Run</button>
	    <button onClick={end_experiment}>End</button>
	</div>
    );
};
