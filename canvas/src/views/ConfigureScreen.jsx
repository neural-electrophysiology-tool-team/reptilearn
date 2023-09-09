/**
 * Author: Tal Eisenberg (2023)
 */

import { useForm } from 'react-hook-form';
import { get_configuration, location_for_canvas_id, set_configuration } from '../common';
import React from 'react';

export const ConfigureScreen = () => {
  // TODO: Make an MQTT connection and subscribe to canvas/+/out/connected as connected messages arrive show them and use for validation (should be unique) 
  const config = get_configuration() || {
    canvas_id: null,
    mqtt_address: { host: 'localhost', port: '9001' },
  };

  const { register, handleSubmit } = useForm({
    defaultValues: config,
  });
  const [canvas_id, setCanvasId] = React.useState(config.canvas_id);

  const onSubmit = (config) => {
    config.mqtt_address.port = JSON.parse(config.mqtt_address.port);
    set_configuration(config);
    window.location = location_for_canvas_id(config.canvas_id);
  }

  const handleChange = (e) => {
    if (e.target.name !== "canvas_id") {
      return;
    }

    setCanvasId(e.target.value);
  }

  return (
    <div className="w-full max-w-xs">
      <div className="flex rounded-md items-center justify-center bg-gray-500 py-12 px-4 my-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div className="text-3xl font-bold">Canvas settings</div>
          <form onSubmit={handleSubmit(onSubmit)} onChange={handleChange}>
            <div>
              <label htmlFor="canvasId" className="block text-sm font-medium text-gray-700">Canvas ID</label>
              <input id="canvasId" type="text" {...register("canvas_id", { required: true })} className="mt-1 p-1 block w-full shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm border-gray-300 rounded-md" />
            </div>

            <div className="mt-6">
              <label htmlFor="mqttHost" className="block text-sm font-medium text-gray-700">MQTT Host</label>
              <input id="mqttHost" type="text" {...register("mqtt_address.host", { required: true })} className="mt-1 p-1 block w-full shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm border-gray-300 rounded-md" />
            </div>

            <div className="mt-6">
              <label htmlFor="mqttPort" className="block text-sm font-medium text-gray-700">MQTT Port</label>
              <input id="mqttPort" type="number" min={1} max={65535} {...register("mqtt_address.port", { required: true })} className="mt-1 p-1 block w-full shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm border-gray-300 rounded-md" />
            </div>

            <button disabled={!canvas_id} type="submit" className="w-full flex flex-col items-center py-2 px-4 mt-8 border border-transparent text-sm font-medium rounded-md bg-slate-300 p-2 text-gray-700 hover:bg-slate-600 hover:text-gray-100 disabled:bg-slate-300 disabled:text-gray-400">
              <div className='font-bold'>Connect</div>
              {canvas_id && <div className="w-full text-center text-xs">{location_for_canvas_id(canvas_id)}</div>}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
