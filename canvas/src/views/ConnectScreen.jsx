/**
 * Author: Tal Eisenberg (2023)
 */

import { get_configuration } from "../common";

/* eslint-disable react/prop-types */
export const ConnectScreen = ({ failed }) => {
  const mqtt_address = get_configuration()?.mqtt_address;
  
  const configure_link = (
    <div><a className="rounded-md bg-slate-300 p-2 text-gray-700 hover:bg-slate-600 hover:text-gray-100" href={window.location.origin}>Configure</a></div>
  );

  if (!mqtt_address) {
    return configure_link;
  }

  if (failed) {
    return (
      <div className='text-center'>
        <div className='pb-4'>Connection to {mqtt_address.host}:{mqtt_address.port} failed. Retrying...</div>
        {configure_link}
      </div>
    )
  }

  return (
    <>
      <div>Connecting to {mqtt_address.host}:{mqtt_address.port}...</div>
    </>
  )
}