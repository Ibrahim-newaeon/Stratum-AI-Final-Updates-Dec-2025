import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { cn } from '@/lib/utils';

interface PlatformData {
  name: string;
  value: number;
  color: string;
}

interface PlatformBreakdownWidgetProps {
  data?: PlatformData[];
  className?: string;
}

export function PlatformBreakdownWidget({ data, className }: PlatformBreakdownWidgetProps) {
  if (!data || data.length === 0) {
    return (
      <div className={cn('h-full p-4 flex items-center justify-center', className)}>
        <p className="text-sm text-muted-foreground">No platform data available</p>
      </div>
    );
  }

  return (
    <div className={cn('h-full p-4', className)}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
            formatter={((value: number) => [`${value}%`, 'Share']) as any}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            formatter={(value) => <span className="text-xs text-foreground">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
