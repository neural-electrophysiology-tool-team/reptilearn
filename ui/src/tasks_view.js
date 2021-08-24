import React from 'react';
import { Modal, Icon, Dropdown, Button } from 'semantic-ui-react';
import {api_url} from './config.js';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

export const TasksView = () => {
    const [taskModule, setTaskModule] = React.useState(null);
    const [taskList, setTaskList] = React.useState([]);
    const [isLoading, setLoading] = React.useState(false);
    const [showDatePicker, setShowDatePicker] = React.useState(false);
    const [scheduleDate, setScheduleDate] = React.useState(new Date());
    const [selectedTask, setSelectedTask] = React.useState(null);
    
    const load_task_list = () => {
        setLoading(true);
        fetch(api_url + "/task/list")
            .then(res => res.json())
            .then(tasks => {
                setTaskList(tasks);
                setLoading(false);
            });
    };

    const run_task = (mod, task) => {
        fetch(api_url + `/task/run/${mod}/${task}`);
    };

    const schedule_task = (mod, task) => {
        setShowDatePicker(false);
        fetch(api_url + `/task/schedule/${mod}/${task}`, {
            method: "POST",
            headers: {
		"Accept": "application/json",
		"Content-Type": "application/json"
	    },
	    body: JSON.stringify(scheduleDate)
        });
    };

    const open_datepicker_modal = (mod, task) => {
        setShowDatePicker(true);
        setSelectedTask([mod, task]);
    };
    
    const date_picker = selectedTask ? (
        <Modal size="small"
               onClose={() => setShowDatePicker(false)}
               onOpen={() => setShowDatePicker(true)}
               open={showDatePicker}>
          <Modal.Header>Schedule task <em>{selectedTask[1]}</em></Modal.Header>
          <Modal.Content>
            <label>Choose date and time:</label>
            <DatePicker selected={scheduleDate}
                        onChange={setScheduleDate}
                        showTimeSelect
                        popperPlacement="bottom-start"
                        dateFormat="Pp"/>
            
          </Modal.Content>
          <Modal.Actions>
            <Button primary onClick={() => schedule_task(selectedTask[0], selectedTask[1])}>
              Schedule
            </Button>
            <Button onClick={() => setShowDatePicker(false)}>Cancel</Button>
          </Modal.Actions>
        </Modal>
    ) : null;
    
    const task_items = (mod, task) => (
        <Dropdown.Item>
          <Button.Group>
          <Button attached='left' compact size="mini" icon labelPosition='right' onClick={() => run_task(mod, task)}>
            {task}
            <Icon name='play circle outline'/>
          </Button>
          <Button attached='right' compact size="mini" icon onClick={() => open_datepicker_modal(mod, task)}>
            <Icon name='clock'/>
        </Button>
        </Button.Group>
        </Dropdown.Item>   
    );

    const items = Object.keys(taskList).map(mod => (
        <React.Fragment>
          <Dropdown.Header>{mod}</Dropdown.Header>
          {taskList[mod].map(task => task_items(mod, task))}
          <Dropdown.Divider/>
        </React.Fragment>        
    ));
    
    return (
        <React.Fragment>
          {date_picker}
          <button>       
            <Dropdown text='Tasks'
                      onOpen={load_task_list}
                      loading={isLoading}
                      scrolling> 
              <Dropdown.Menu>
                {items}
              </Dropdown.Menu>
            </Dropdown>
          </button>          
        </React.Fragment>
    );
};
