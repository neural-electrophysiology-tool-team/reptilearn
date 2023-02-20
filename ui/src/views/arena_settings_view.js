import React from 'react';
import { useSelector, useDispatch } from 'react-redux';

import { setArenaConfig } from '../store/reptilearn_slice';
import RLModal from './ui/modal.js';
import { RLSimpleListbox } from './ui/list_box.js';
import { RLJSONEditor } from './ui/json_edit.js';
import RLButton from './ui/button.js';
import { Bar } from './ui/bar.js';
import RLInput from './ui/input.js';
import { classNames } from './ui/common.js';
import { api } from '../api';
import deep_equal from 'deep-equal';

export const ArenaSettingsView = ({ setOpen, open }) => {
    const dispatch = useDispatch();

    const [openAddModal, setOpenAddModal] = React.useState(false);
    const [addPortInput, setAddPortInput] = React.useState(null);
    const [addSerialNumberInput, setAddSerialNumberInput] = React.useState(null);
    const [addFQBNInput, setAddFQBNInput] = React.useState(null);
    const [addNameInput, setAddNameInput] = React.useState(null);

    const [editedConfig, setEditedConfig] = React.useState(null);
    const [selectedPort, setSelectedPort] = React.useState(null);
    const [isLoadingConfig, setLoadingConfig] = React.useState(true);

    const [availablePorts, setAvailablePorts] = React.useState(null);

    const arena_config = useSelector((state) => state.reptilearn.arenaConfig);
    const ctrl_state = useSelector((state) => state.reptilearn.ctrlState);

    // TODO: this is copied from App.js. should be somewhere else...
    const fetch_arena_config = React.useCallback(() => {
        api.arena.get_ports()
            .then(setAvailablePorts);

        return api.arena.get_config()
            .then((config) => {
                dispatch(setArenaConfig(config));
                setEditedConfig(config);
                return config;
            })
            .catch(err => {
                console.log(`Error while fetching video config: ${err}`);
                setTimeout(fetch_arena_config, 5000);
            });
    }, [dispatch]);
    
    React.useEffect(() => {
        if (!openAddModal) {
            return;
        }

        api.arena.get_ports()
            .then((ports) => ports.filter((p) => !Object.values(editedConfig).map((c) => c.serial_number).includes(p.serial_number)))
            .then(setAvailablePorts);
    }, [openAddModal]);

    React.useEffect(() => {
        if (!open) {
            return;
        }

        fetch_arena_config().then((config) => {
            setLoadingConfig(false);

            if (Object.keys(config).length > 0) {
                setSelectedPort(Object.keys(config)[0]);
            }
        });

    }, [open]);

    const apply = () => {
        setOpen(false);
        api.arena.update_config(editedConfig)
            .then((resp) => {
                if (fetch_arena_config) {
                    return fetch_arena_config();
                }
                else {
                    return resp;
                }
            })
            .then(() => {
                if (ctrl_state.arena?.listening) {
                    api.arena.restart_bridge();
                }
            })
            .catch((e) => {
                console.log("Error while updating config:", e);
            });
    };

    const open_add_modal = () => {
        setAddNameInput('');
        setAddSerialNumberInput('');
        setAddFQBNInput('');
        setAddPortInput(null);

        setOpenAddModal(true);
    };

    const on_select_add_port = (c) => {
        setAddPortInput(c);
        setAddSerialNumberInput(c.serial_number);
    }

    const add_port = async () => {
        const cfg = { ...editedConfig };

        cfg[addNameInput] = {
            serial_number: addSerialNumberInput,
            fqbn: addFQBNInput,
            allow_get: true,
            interfaces: [],
        };

        setEditedConfig(cfg);
        setSelectedPort(addNameInput);

        setOpenAddModal(false);
    };

    const remove_port = () => {
        const cfg = { ...editedConfig };
        delete cfg[selectedPort];

        setEditedConfig(cfg);
        setSelectedPort(Object.keys(cfg)[0]);
    };

    const on_config_changed = (config, port_name) => {
        const c = { ...editedConfig };
        c[port_name] = config;
        setEditedConfig(c);
    };

    const upload_program = async (port_name) => {
        if (ctrl_state.arena?.listening) {
            await api.arena.stop_bridge();
        }
        api.arena.upload_program(port_name);
    };

    const dirty = !deep_equal(editedConfig, arena_config);

    const port_options = editedConfig ? Object.keys(editedConfig).map(port => ({
        key: port,
        label: port,
        value: port
    })) : null;

    const add_modal = openAddModal && (
        <RLModal open={openAddModal} setOpen={setOpenAddModal} sizeClasses="w-3/6 h-1/3" header={<>Add Arduino port</>} actions={
            <>
                <RLButton.ModalButton onClick={add_port} disabled={
                    !addSerialNumberInput || addSerialNumberInput.trim().length === 0 || !addPortInput ||
                    !addFQBNInput || addFQBNInput.trim().length === 0
                }>
                    Add
                </RLButton.ModalButton>
                <RLButton.ModalButton onClick={() => setOpenAddModal(false)}>Cancel</RLButton.ModalButton>
            </>
        }>
            <table className="border-separate [border-spacing:0.75rem] w-full">
                <tbody>
                    <tr>
                        <td>Port:</td>
                        <td>
                            {availablePorts?.length ? <RLSimpleListbox
                                className="w-full"
                                placeholder={`Select Arduino port...`}
                                setSelected={on_select_add_port}
                                selected={addPortInput}
                                options={availablePorts.map((c) => ({ label: `${c.description} (${c.device})`, key: c.serial_number, value: c }))} />
                                : <div>No available ports</div>}
                        </td>
                    </tr>
                    <tr>
                        <td>
                            Name:
                        </td>
                        <td>
                            <RLInput.Text
                                placeholder={"Arduino port name"}
                                value={addNameInput}
                                onChange={(e) => setAddNameInput(e.target.value)}
                                className={classNames("w-full")} />
                        </td>
                    </tr>
                    <tr>
                        <td>
                            Serial number:
                        </td>
                        <td>
                            <RLInput.Text
                                placeholder={"Arduino serial number"}
                                value={addSerialNumberInput}
                                onChange={(e) => setAddSerialNumberInput(e.target.value)}
                                className={classNames("w-full")} />
                        </td>
                    </tr>
                    <tr>
                        <td>
                            FQBN:
                        </td>
                        <td>
                            <RLInput.Text
                                placeholder={"Arduino board FQBN"}
                                value={addFQBNInput}
                                onChange={(e) => setAddFQBNInput(e.target.value)}
                                className={classNames("w-full")} />
                        </td>
                    </tr>
                </tbody>
            </table>
        </RLModal>
    );

    const apply_label = ctrl_state.arena?.listening ? "Save & Restart" : "Save"
    
    return (
        <RLModal open={open} setOpen={setOpen} header="Arena settings" sizeClasses="w-3/6 h-4/6" contentOverflowClass="overflow-hidden" actions={
            <>
                {dirty && <RLButton.ModalButton colorClasses="text-green-500" onClick={apply}>{apply_label}</RLButton.ModalButton>}
                <RLButton.ModalButton onClick={() => setOpen(false)}>{dirty ? "Cancel" : "Close"}</RLButton.ModalButton>
            </>
        }>
            {!isLoadingConfig ? <div className="flex flex-col w-100">
                {add_modal}
                <Bar colors="bg-gray-100">
                    <span>Arduino port:</span>
                    <RLSimpleListbox
                        options={port_options}
                        selected={selectedPort}
                        setSelected={setSelectedPort} />
                    <RLButton.BarButton onClick={open_add_modal} icon="add" />
                    <RLButton.BarButton onClick={remove_port} icon="xmark" disabled={!selectedPort} />
                    <RLButton.BarButton onClick={() => upload_program(selectedPort)} icon="upload" text="Upload program" iconClassName="mr-1" disabled={!selectedPort}/>
                </Bar>
                {selectedPort && <RLJSONEditor
                    mainMenuBar={false}
                    navigationBar={false}
                    className="p-1 overflow-y-auto flex-grow"
                    content={{ json: editedConfig[selectedPort] }}
                    onChange={(updatedContent) => on_config_changed(updatedContent.json, selectedPort)} />}
            </div> : <div>Loading...</div>}
        </RLModal >
    );
};
