import React from 'react';
import { Table, Grid, Checkbox, Modal, Tab, Dropdown, Button, Input } from 'semantic-ui-react';
import {api_url} from './config.js';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

export const TasksView = () => {
    const [taskList, setTaskList] = React.useState([]);
    const [isLoading, setLoading] = React.useState(false);

    const [showTaskListModal, setShowTaskListModal] = React.useState(false);
    const [isLoadingScheduledTasks, setLoadingScheduledTasks] = React.useState(false);
    const [scheduledTasks, setScheduledTasks] = React.useState([]);
    
    const [showScheduleModal, setShowScheduleModal] = React.useState(false);
    const [scheduleDate, setScheduleDate] = React.useState(new Date());
    const [scheduleInterval, setScheduleInterval] = React.useState(1);
    const [scheduleIntervalUnit, setScheduleIntervalUnit] = React.useState(1);
    const [scheduleRepeats, setScheduleRepeats] = React.useState(1);
    const [selectedTask, setSelectedTask] = React.useState(null);
    const [activeTabIdx, setActiveTabIdx] = React.useState(0);
    
    const load_task_list = () => {
        setLoading(true);
        fetch(api_url + "/task/list")
            .then(res => res.json())
            .then(tasks => {
                setTaskList(tasks);
                setLoading(false);
            });
    };

    // const run_task = (mod, task) => {
    //     fetch(api_url + `/task/run/${mod}/${task}`);
    // };

    const schedule_task = (mod, task) => {
        let args;
        switch (activeTabIdx) {
        case 0:
            args = {
                task_type: 'datetime',
                dt: scheduleDate
            };
            break;
        case 1:
            args = {
                task_type: 'interval',
                interval: scheduleInterval * scheduleIntervalUnit,
                repeats: scheduleRepeats
            };
            break;
        case 2:
            args = {
                task_type: 'timeofday',
                dt: scheduleDate,
                repeats: scheduleRepeats
            };
            break;
        default:
            args = {};
            break;
        }
        
        setShowScheduleModal(false);
        fetch(api_url + `/task/schedule/${mod}/${task}`, {
            method: "POST",
            headers: {
		"Accept": "application/json",
		"Content-Type": "application/json"
	    },
	    body: JSON.stringify(args)
        });
    };

    const open_schedule_modal = () => {
        setScheduleDate(new Date());
        setShowScheduleModal(true);
    };

    const open_task_list_modal = () => {
        setLoadingScheduledTasks(true);
        fetch(api_url + '/task/scheduled_tasks')
            .then(res => res.json())
            .then(tasks => {
                for (let task of Object.values(tasks)) {
                    task.checked = false;
                }
                setScheduledTasks(tasks);
                setLoadingScheduledTasks(false);
                setShowTaskListModal(true);
            });
    };

    const update_task_check = (idx, checked) => {
        const tasks = scheduledTasks.slice();
        tasks[idx].checked = checked;
        setScheduledTasks(tasks);
    };

    const get_checked_tasks = () => {
        return scheduledTasks.filter(t => t.checked);
    };

    const cancel_checked_tasks = () => {
        get_checked_tasks().forEach(t => {
            fetch(api_url + `/task/cancel/${t.task_id}`)
                .then(open_task_list_modal);
        });
    };
    
    const unit_options = [
        {text: 'milliseconds', value: 0.001, key: 0.001},
        {text: 'seconds', value: 1, key: 1},
        {text: 'minutes', value: 60, key: 60},
        {text: 'hours', value: 60*60, key: 60*60},
        {text: 'days', value: 24*60*60, key: 24*60*60}];
    
    const repeat_options = [
        {
            text: 'forever',
            value: true,
            key: 'forever',
        },
        {
            text: 'once',
            value: 1,
            key: 1
        },
        {
            text: 'twice',
            value: 2,
            key: 2
        }
    ];
    for (let i of [3,4,5,6,7,8,9,10]) {
        repeat_options.push({
            text: `${i} times`,
            value: i,
            key: i
        });
    }
        
    const panes = [
        { menuItem: 'Interval', render: () => (
            <Tab.Pane>
              <table>
                <tbody>
                  <tr>
                    <td>Run task in:</td>
                    <td>
                      <Input label={
                          <Dropdown options={unit_options}
                                    value={scheduleIntervalUnit}
                                    onChange={(e, { value }) => setScheduleIntervalUnit(value)}
                          />
                      }
                             size="small"
                             style={{width: '80px'}}
                             labelPosition="right"
                             value={scheduleInterval}
                             onChange={(e, { value }) => setScheduleInterval(parseInt(value))}/>    
                    </td>
                  </tr>
                  <tr>
                    <td>Repeats:</td>
                    <td>
                      <Dropdown options={repeat_options}
                                value={scheduleRepeats}
                                onChange={(e, {value}) => setScheduleRepeats(value)}
                                scrolling
                                selection/>
                    </td>
                  </tr>
                </tbody>
              </table>
            </Tab.Pane>
        )},
        { menuItem: 'Date/Time', render: () => (
            <Tab.Pane>
              <p>Run the task at a specific date and time:</p>
              <DatePicker selected={scheduleDate}
                          onChange={setScheduleDate}
                          showTimeSelect
                          timeIntervals={15}
                          showPopperArrow={false}
                          popperPlacement="bottom-start"
                          dateFormat="Pp"/>
            </Tab.Pane>
        ) },        
        { menuItem: 'Time of day', render: () => (
            <Tab.Pane>
              <table>
                <tbody>
                  <tr>
                    <td>Run today or tomorrow at:</td>
                    <td>
                      <DatePicker selected={scheduleDate}
                                  onChange={setScheduleDate}
                                  showTimeSelect
                                  showTimeSelectOnly
                                  popperPlacement="bottom-start"
                                  showPopperArrow={false}
                                  timeIntervals={15}
                                  dateFormat="h:mm aa"/>
                    </td>
                  </tr>
                  <tr>
                    <td>Repeat daily:</td>
                    <td>
                      <Dropdown options={repeat_options}
                                value={scheduleRepeats}
                                onChange={(e, {value}) => setScheduleRepeats(value)}
                                scrolling
                                selection/>
                    </td>                                      
                  </tr>
                </tbody>
              </table>
            </Tab.Pane>
        )},

    ];    

    const schedule_modal = (
        <Modal size="small"
               onClose={() => setShowScheduleModal(false)}
               onOpen={() => setShowScheduleModal(true)}
               open={showScheduleModal}>
          <Modal.Header>Schedule task</Modal.Header>
          <Modal.Content>
            <Grid columns={2} verticalAlign='middle'>
              <Grid.Row>
                <Grid.Column>
                  <Dropdown className="selection"
                            placeholder={selectedTask ? selectedTask[0] + "." + selectedTask[1] : "Select task"}
                            value={'' + selectedTask}>
                    <Dropdown.Menu>
                      <React.Fragment>
                        {Object.keys(taskList).map(mod => {
                            const tasks = taskList[mod];

                            return (
                                <React.Fragment key={mod}>
                                  <Dropdown.Header>{mod}</Dropdown.Header>
                                  {tasks.map(task => (
                                      <Dropdown.Item text={task}
                                                     key={'' + [mod, task]}
                                                     value={'' + [mod, task]}
                                                     onClick={() => setSelectedTask([mod, task])}/>
                                  ))}
                                </React.Fragment>
                            );
                        })}
                      </React.Fragment>
                    </Dropdown.Menu>
                  </Dropdown>
                </Grid.Column>
              </Grid.Row>
              <Grid.Row>
                <Grid.Column width={16}>
                  <Tab menu={{ fluid: true, vertical: true }} panes={panes} activeIndex={activeTabIdx}
                       onTabChange={(e, data) => setActiveTabIdx(data.activeIndex)}/>
                </Grid.Column>
              </Grid.Row>
            </Grid>
          </Modal.Content>
          <Modal.Actions>
            {selectedTask ? (
                <Button primary onClick={() => schedule_task(selectedTask[0], selectedTask[1])}>
                  Schedule
                </Button>
            ) : null}
            <Button onClick={() => setShowScheduleModal(false)}>Cancel</Button>
          </Modal.Actions>
        </Modal>
    );

    const task_list_modal = (
        <Modal size="small"
               onClose={() => setShowTaskListModal(false)}
               onOpen={() => setShowTaskListModal(true)}
               open={showTaskListModal}>
          <Modal.Header>Scheduled tasks</Modal.Header>
          <Modal.Content>
        {scheduledTasks.length > 0 ? (
            <Table striped celled size="small">
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell/>
                  <Table.HeaderCell>Task</Table.HeaderCell>
                  <Table.HeaderCell>Schedule</Table.HeaderCell>
                  <Table.HeaderCell>Parameters</Table.HeaderCell>
                  <Table.HeaderCell>Created at</Table.HeaderCell>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                { scheduledTasks.map((t, i) => (
                    <Table.Row key={i}>
                      <Table.Cell><Checkbox checked={t.checked} onChange={(e, { checked }) => update_task_check(i, checked)}/></Table.Cell>
                      <Table.Cell>{t.task}</Table.Cell>
                      <Table.Cell>{t.task_type}</Table.Cell>
                      <Table.Cell>{JSON.stringify(t.params)}</Table.Cell>
                      <Table.Cell>{t.created}</Table.Cell>
                    </Table.Row>
                ))}
              </Table.Body>              
            </Table>
        ) : "There are no scheduled tasks."}
          </Modal.Content>
          <Modal.Actions>
            <Button negative onClick={cancel_checked_tasks} disabled={get_checked_tasks().length === 0}>Cancel selected</Button>
            <Button onClick={() => setShowTaskListModal(false)}>Close</Button>
          </Modal.Actions>
        </Modal>        
    );
    
    return (
        <React.Fragment>
          {schedule_modal}
          {task_list_modal}
          <Dropdown text='Schedule'
                    onOpen={load_task_list}
                    scrolling
                    item>
            <Dropdown.Menu>
              <Dropdown.Item key='schedule'
                             text='Schedule task'
                             onClick={open_schedule_modal}/>
              <Dropdown.Divider/>
              <Dropdown.Item key='scheduled'
                             text='Show schedules'
                             onClick={open_task_list_modal}>
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        </React.Fragment>
    );
};
