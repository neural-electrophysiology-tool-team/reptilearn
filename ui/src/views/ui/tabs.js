import React from 'react';
import { Tab } from '@headlessui/react';
import { classNames, styles } from './common';

const RLTabs = ({ onChange, selectedIndex, vertical, tabs, className, panelClassName, tabListClassName }) => {
    return (
        <Tab.Group as="div" onChange={onChange} selectedIndex={selectedIndex} vertical={vertical} className={classNames(
            vertical ? 'flex-row' : 'flex-col', 
            "flex flex-grow",
            className)}>

            <Tab.List className={classNames(
                tabListClassName,
                "flex border-gray-100 overflow-hidden",
                vertical ? "flex-col border-r-2 overflow-y-auto" : "flex-row border-b-2 overflow-x-auto")}>

                {tabs.map(({ title }, i) => (
                    <Tab key={i} className={({ selected }) =>
                        classNames(
                            'rounded-none text-base px-2 font-medium hover:border-gray-200 hover:bg-gray-200',
                            vertical ? "rounded-l-md py-2" : "rounded-t-md py-1",
                            selected
                                ? 'bg-gray-100 text-blue-600 ' + (vertical ? 'border-r-0' : 'border-b-0')
                                : 'text-gray-700 border-transparent',
                            styles.focusRing)}>

                        {title}
                    </Tab>
                ))}
            </Tab.List>
            <Tab.Panels className={classNames("flex flex-grow", panelClassName || "overflow-y-scroll")}>
                {tabs.map(({ panel }, i) => (
                    <Tab.Panel key={i} className={classNames(
                        "w-full h-full flex flex-col bg-white border-2  border-gray-100 rounded-[4px]",
                        vertical ? "border-l-0 rounded-l-none" : "border-t-0 rounded-t-none",
                        styles.focusRing)}>

                        {panel}
                    </Tab.Panel>
                ))}
            </Tab.Panels>
        </Tab.Group>
    );
};

export default RLTabs;