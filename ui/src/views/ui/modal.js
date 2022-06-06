import React from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { classNames } from './common';

const RLModal = ({ header, children, actions, open, setOpen, initialFocus, className, sizeClasses, contentOverflowClass}) => {    
    return (
        <Transition.Root show={open} as={React.Fragment}>
            <Dialog as="div" className="relative z-[200] overflow-y-auto" initialFocus={initialFocus} onClose={setOpen}>
                <Transition.Child
                    as={React.Fragment}
                    enter="ease-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in duration-200"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0">

                    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
                </Transition.Child>

                <div className="fixed z-10 inset-0">
                    <div className="flex items-end sm:items-center justify-center h-full p-4 text-center sm:p-0">
                        <Transition.Child
                            as={React.Fragment}
                            enter="ease-out duration-300"
                            enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                            enterTo="opacity-100 translate-y-0 sm:scale-100"
                            leave="ease-in duration-200"
                            leaveFrom="opacity-100 translate-y-0 sm:scale-100"
                            leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                        >
                            <Dialog.Panel className={classNames(
                                "flex flex-col relative rounded-lg text-left overflow-visible shadow-xl transform transition-all", 
                                className, 
                                sizeClasses || "h-4/6 w-512")}>

                                {header ? (
                                    <div className="bg-white rounded-t-lg py-3 px-4 font-bold text-2xl">
                                        {header}
                                    </div>
                                ) : null}
                                <div className={classNames(
                                    "bg-white px-4 pb-4 w-full text-sm flex flex-col flex-grow", 
                                    header ? "" : "pt-5 rounded-t-lg", 
                                    contentOverflowClass ? contentOverflowClass : "overflow-y-auto")}>

                                    {children}
                                </div>
                                <div className="bg-gray-50 rounded-b-lg px-4 py-3 flex flex-row-reverse">
                                    {actions}
                                </div>
                            </Dialog.Panel>
                        </Transition.Child>
                    </div>
                </div>
            </Dialog>
        </Transition.Root>
    )
};

export default RLModal;