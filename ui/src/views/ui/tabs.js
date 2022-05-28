import React from 'react';
import { Tab } from '@headlessui/react';
import { classNames, styles } from './common';

const RLTabs = ({ onChange, selectedIndex, vertical, tabs }) => {
    return (
        <Tab.Group as="div" onChange={onChange} selectedIndex={selectedIndex} vertical={vertical} className={classNames(vertical ? 'flex flex-row' : 'flex-col')}>
            <Tab.List className={classNames("flex", vertical ? "flex-col border-r-2" : "flex-row border-b-2")}>
                {tabs.map(({ title }, i) => (
                    <Tab key={i} className={({ selected }) =>
                        classNames(
                            'rounded-sm text-base mt-2 pt-2 pb-0 px-2 font-medium leading-5 text-gray-700',
                            styles.focusRing,
                            'hover:bg-gray-400',
                            selected
                                ? 'bg-white border-2 ' + (vertical ? 'border-r-0' : 'border-b-0')
                                : 'text-blue-200'
                        )
                    }>{title}</Tab>
                ))}
            </Tab.List>
            <Tab.Panels className={classNames(vertical ? "" : "mt-1")}>
                {tabs.map(({ panel }, i) => (
                    <Tab.Panel key={i} className={classNames(
                        'rounded-sm bg-white',
                        styles.focusRing,
                    )}>
                        {panel}
                    </Tab.Panel>
                ))}
            </Tab.Panels>
        </Tab.Group>
    );
};

export default RLTabs;