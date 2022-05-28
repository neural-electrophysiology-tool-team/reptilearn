import { classNames } from "./common"

export const Bar = ({ title, children, className, colors, ...props }) => {
    return (
        <div {...props} className={classNames(className, "flex flex-row h-[34px] gap-1 p-1 border-b-2", (colors || "bg-gray-300 border-gray-500"))}>
            {title && <span className="font-bold items-center flex pr-1">{title}</span>}
            {children}
        </div>
    );
}
