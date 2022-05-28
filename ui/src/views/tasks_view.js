import React from 'react';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

import { api_url } from '../config.js';
import RLButton from './ui/button.js';
import { RLListbox, RLSimpleListbox } from './ui/list_box.js';
import RLMenu from './ui/menu.js';
import RLModal from './ui/modal.js';
import RLTabs from './ui/tabs.js';

export const TasksView = () => {
    const [taskList, setTaskList] = React.useState([]);
    // const [isLoading, setLoading] = React.useState(false);

    const [showTaskListModal, setShowTaskListModal] = React.useState(false);
    // const [isLoadingScheduledTasks, setLoadingScheduledTasks] = React.useState(false);
    const [scheduledTasks, setScheduledTasks] = React.useState([]);

    const [showScheduleModal, setShowScheduleModal] = React.useState(false);
    const [scheduleDate, setScheduleDate] = React.useState(new Date());
    const [scheduleInterval, setScheduleInterval] = React.useState(1);
    const [scheduleIntervalUnit, setScheduleIntervalUnit] = React.useState(1);
    const [scheduleRepeats, setScheduleRepeats] = React.useState(1);
    const [selectedTask, setSelectedTask] = React.useState(null);
    const [activeTabIdx, setActiveTabIdx] = React.useState(0);

    const load_task_list = () => {
        // setLoading(true);
        fetch(api_url + "/task/list")
            .then(res => res.json())
            .then(tasks => {
                setTaskList(tasks);
                // setLoading(false);
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
                    task_type: 'interval',
                    interval: scheduleInterval * scheduleIntervalUnit,
                    repeats: scheduleRepeats
                };
                break;
            case 1:
                args = {
                    task_type: 'datetime',
                    dt: scheduleDate
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

    const open_schedule_modal = async () => {
        await load_task_list();
        setScheduleDate(new Date());
        setShowScheduleModal(true);
    };

    const open_task_list_modal = () => {
        // setLoadingScheduledTasks(true);
        fetch(api_url + '/task/scheduled_tasks')
            .then(res => res.json())
            .then(tasks => {
                for (let task of Object.values(tasks)) {
                    task.checked = false;
                }
                setScheduledTasks(tasks);
                // setLoadingScheduledTasks(false);
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
        { label: 'milliseconds', value: 0.001, key: 0.001 },
        { label: 'seconds', value: 1, key: 1 },
        { label: 'minutes', value: 60, key: 60 },
        { label: 'hours', value: 60 * 60, key: 60 * 60 },
        { label: 'days', value: 24 * 60 * 60, key: 24 * 60 * 60 }];

    const repeat_options = [
        { label: 'forever', value: true, key: 'forever' },
        { label: 'once', value: 1, key: 1 },
        { label: 'twice', value: 2, key: 2 }];

    for (let i of [3, 4, 5, 6, 7, 8, 9, 10]) {
        repeat_options.push({
            label: `${i} times`,
            value: i,
            key: i
        });
    }

    const schedule_modal = (
        <RLModal open={showScheduleModal} setOpen={setShowScheduleModal} header="Schedule task" sizeClasses="w-3/6" actions={
            <>
                {selectedTask ? (
                    <RLButton.ModalButton onClick={() => schedule_task(selectedTask[0], selectedTask[1])}>
                        Schedule
                    </RLButton.ModalButton>
                ) : null}
                <RLButton.ModalButton onClick={() => setShowScheduleModal(false)}>Cancel</RLButton.ModalButton>
            </>
        }>
            <table>
                <tbody>
                    <tr>
                        <td>
                            <RLListbox
                                header={selectedTask ? selectedTask[0] + "." + selectedTask[1] : "Select task"}
                                value={JSON.stringify(selectedTask)}
                                onChange={(sel) => setSelectedTask(JSON.parse(sel))}>

                                {Object.keys(taskList).map(mod => {
                                    const tasks = taskList[mod];

                                    return (
                                        <React.Fragment key={mod}>
                                            <RLListbox.HeaderOption key={mod}>{mod}</RLListbox.HeaderOption>
                                            {tasks.map(task => (
                                                <RLListbox.CheckedOption
                                                    key={JSON.stringify([mod, task])}
                                                    value={JSON.stringify([mod, task])}
                                                    label={task} />
                                            ))}
                                        </React.Fragment>
                                    );
                                })}
                            </RLListbox>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <RLTabs onChange={(index) => setActiveTabIdx(index)} vertical tabs={[
                                {
                                    title: 'Interval',
                                    panel: (
                                        <>
                                            <table>
                                                <tbody>
                                                    <tr>
                                                        <td>Run task in:</td>
                                                        <td className='flex flex-row'>
                                                            <input type="text" className="w-20" value={scheduleInterval} onChange={(e) => setScheduleInterval(e.target.value)} />
                                                            <label>
                                                                <RLSimpleListbox options={unit_options} selected={scheduleIntervalUnit} setSelected={setScheduleIntervalUnit}/>
                                                            </label>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>Repeats:</td>
                                                        <td>
                                                            <RLSimpleListbox options={repeat_options} selected={scheduleRepeats} setSelected={setScheduleRepeats}/>
                                                        </td>
                                                    </tr>
                                                </tbody>
                                            </table>

                                        </>
                                    ),
                                },
                                {
                                    title: 'Date/Time',
                                    panel: (
                                        <>
                                            <p>Run the task at a specific date and time:</p>
                                            <DatePicker selected={scheduleDate}
                                                onChange={setScheduleDate}
                                                showTimeSelect
                                                timeIntervals={15}
                                                showPopperArrow={false}
                                                popperPlacement="bottom-start"
                                                dateFormat="Pp" />

                                        </>
                                    ),
                                },
                                {
                                    title: 'Time of day',
                                    panel: (
                                        <>
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
                                                                dateFormat="h:mm aa" />
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>Repeat daily:</td>
                                                        <td>
                                                            <RLSimpleListbox options={repeat_options} selected={scheduleRepeats} setSelected={setScheduleRepeats}/>
                                                        </td>
                                                    </tr>
                                                </tbody>
                                            </table>

                                        </>
                                    ),
                                },
                            ]} />
                        </td>
                    </tr>
                </tbody>
            </table>
        </RLModal>
    );

    const task_list_modal = (
        <RLModal sizeClasses="w-3/6"
            open={showTaskListModal} setOpen={setShowTaskListModal} header="Scheduled tasks" actions={
                <>
                    <RLButton.ModalButton onClick={cancel_checked_tasks} disabled={get_checked_tasks().length === 0}>Cancel selected</RLButton.ModalButton>
                    <RLButton.ModalButton onClick={() => setShowTaskListModal(false)}>Close</RLButton.ModalButton>
                </>
            }>
            {scheduledTasks.length > 0 ? (
                <table>
                    <tbody>
                        <th>
                            <td></td>
                            <td>Task</td>
                            <td>Schedule</td>
                            <td>Parameters</td>
                            <td>Created at</td>
                        </th>
                        {scheduledTasks.map((t, i) => (
                            <tr key={i}>
                                <td><input type="checkbox" checked={t.checked} onChange={(e) => update_task_check(i, e.target.value)} /></td>
                                <td>{t.task}</td>
                                <td>{t.task_type}</td>
                                <td>{JSON.stringify(t.params)}</td>
                                <td>{t.created}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : "There are no scheduled tasks."}
        </RLModal>
    );

    return (
        <React.Fragment>
            {schedule_modal}
            {task_list_modal}
            <RLMenu button={<RLMenu.TopBarMenuButton title="Schedule"/>}>
                <React.Fragment>
                    <RLMenu.ButtonItem onClick={open_schedule_modal}>Schedule task</RLMenu.ButtonItem>
                    <RLMenu.ButtonItem onClick={open_task_list_modal}>Show schedules</RLMenu.ButtonItem>
                </React.Fragment>
            </RLMenu>
        </React.Fragment>
    );
};
