import { classNames } from "./common"

export const Bar = ({ title, children, className, colors, border, ...props }) => {
    return (
        <div {...props} className={classNames(
            className,
            "flex flex-row gap-1 p-[2px] overflow min-h-[28px]",
            (colors || "bg-gray-300 border-gray-500"),
            (border === 'top' ? 'border-t-2' : 'border-b-2'))}>

            {title && <span className="font-bold items-center flex pr-1">{title}</span>}
            {children}
        </div>
    );
}
