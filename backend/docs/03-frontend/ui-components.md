# UI Components

## Overview

Stratum AI uses a component library built on Radix UI primitives with Tailwind CSS styling.

---

## Component Architecture

```
components/
├── ui/                 # Base UI components (shadcn/ui style)
│   ├── button.tsx
│   ├── dialog.tsx
│   ├── dropdown-menu.tsx
│   ├── input.tsx
│   ├── select.tsx
│   ├── tabs.tsx
│   ├── toast.tsx
│   └── ...
├── common/             # Shared utility components
│   ├── LoadingSpinner.tsx
│   ├── ErrorBoundary.tsx
│   ├── EmptyState.tsx
│   └── ...
├── charts/             # Chart components
│   ├── LineChart.tsx
│   ├── BarChart.tsx
│   └── ...
├── cdp/                # CDP-specific components
│   ├── ProfileCard.tsx
│   ├── SegmentBuilder.tsx
│   └── ...
└── auth/               # Auth components
    ├── ProtectedRoute.tsx
    └── OnboardingGuard.tsx
```

---

## Base UI Components

### Button

```tsx
import { Button } from '@/components/ui/button'

// Variants
<Button>Default</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Outline</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link</Button>

// Sizes
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>
<Button size="icon"><Icon /></Button>

// States
<Button disabled>Disabled</Button>
<Button isLoading>Loading</Button>
```

### Dialog

```tsx
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

<Dialog>
  <DialogTrigger asChild>
    <Button>Open Dialog</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Dialog Title</DialogTitle>
      <DialogDescription>
        Description text goes here.
      </DialogDescription>
    </DialogHeader>
    <div>Content</div>
    <DialogFooter>
      <Button>Save</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Input

```tsx
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

<div className="space-y-2">
  <Label htmlFor="email">Email</Label>
  <Input
    id="email"
    type="email"
    placeholder="Enter email"
  />
</div>
```

### Select

```tsx
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select'

<Select value={value} onValueChange={setValue}>
  <SelectTrigger>
    <SelectValue placeholder="Select option" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="meta">Meta</SelectItem>
    <SelectItem value="google">Google</SelectItem>
    <SelectItem value="tiktok">TikTok</SelectItem>
  </SelectContent>
</Select>
```

### Tabs

```tsx
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from '@/components/ui/tabs'

<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="analytics">Analytics</TabsTrigger>
    <TabsTrigger value="settings">Settings</TabsTrigger>
  </TabsList>
  <TabsContent value="overview">Overview content</TabsContent>
  <TabsContent value="analytics">Analytics content</TabsContent>
  <TabsContent value="settings">Settings content</TabsContent>
</Tabs>
```

### Toast

```tsx
import { useToast } from '@/components/ui/use-toast'
import { Toaster } from '@/components/ui/toaster'

// Add Toaster to App
<App>
  {children}
  <Toaster />
</App>

// Use in components
function Component() {
  const { toast } = useToast()

  const handleClick = () => {
    toast({
      title: 'Success',
      description: 'Campaign saved successfully',
      variant: 'default', // or 'destructive'
    })
  }
}
```

### Dropdown Menu

```tsx
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost">
      <MoreHorizontal />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent>
    <DropdownMenuItem onClick={handleEdit}>
      Edit
    </DropdownMenuItem>
    <DropdownMenuItem onClick={handleDuplicate}>
      Duplicate
    </DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem
      className="text-destructive"
      onClick={handleDelete}
    >
      Delete
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

---

## Common Components

### LoadingSpinner

```tsx
import LoadingSpinner from '@/components/common/LoadingSpinner'

<LoadingSpinner />
<LoadingSpinner size="sm" />
<LoadingSpinner size="lg" />
```

### EmptyState

```tsx
import { EmptyState } from '@/components/common/EmptyState'

<EmptyState
  icon={<FolderIcon />}
  title="No campaigns"
  description="Get started by creating your first campaign"
  action={
    <Button onClick={handleCreate}>Create Campaign</Button>
  }
/>
```

### ErrorBoundary

```tsx
import { ErrorBoundary } from '@/components/common/ErrorBoundary'

<ErrorBoundary fallback={<ErrorPage />}>
  <ChildComponent />
</ErrorBoundary>
```

---

## Chart Components

### Line Chart

```tsx
import { LineChart } from '@/components/charts/LineChart'

<LineChart
  data={data}
  xKey="date"
  yKey="value"
  title="Performance Over Time"
/>
```

### Bar Chart

```tsx
import { BarChart } from '@/components/charts/BarChart'

<BarChart
  data={data}
  xKey="platform"
  yKey="spend"
  title="Spend by Platform"
/>
```

### Metric Card

```tsx
import { MetricCard } from '@/components/charts/MetricCard'

<MetricCard
  title="Total Spend"
  value="$15,420"
  change={+12.5}
  trend="up"
/>
```

---

## Form Components

### With React Hook Form

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const schema = z.object({
  name: z.string().min(1, 'Required'),
  email: z.string().email('Invalid email'),
})

function CampaignForm() {
  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: { name: '', email: '' },
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Submit</Button>
      </form>
    </Form>
  )
}
```

---

## Component Variants (CVA)

Using Class Variance Authority:

```tsx
import { cva, type VariantProps } from 'class-variance-authority'

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground',
        outline: 'border border-input bg-background hover:bg-accent',
        secondary: 'bg-secondary text-secondary-foreground',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}
```

---

## Component Composition

### Compound Components

```tsx
// Table compound component
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Name</TableHead>
      <TableHead>Status</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>Campaign A</TableCell>
      <TableCell>Active</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### Render Props

```tsx
<DataTable
  data={campaigns}
  columns={columns}
  renderRow={(row) => (
    <TableRow key={row.id}>
      <TableCell>{row.name}</TableCell>
    </TableRow>
  )}
/>
```

---

## Responsive Components

```tsx
// Hide on mobile
<div className="hidden md:block">
  Desktop only content
</div>

// Show only on mobile
<div className="block md:hidden">
  Mobile only content
</div>

// Responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {items.map(item => <Card key={item.id} {...item} />)}
</div>
```

---

## Animation Patterns

### Framer Motion

```tsx
import { motion } from 'framer-motion'

<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -20 }}
  transition={{ duration: 0.2 }}
>
  Animated content
</motion.div>
```

### Tailwind Animations

```tsx
// Built-in animations from tailwind.config.js
<div className="animate-fade-in">Fade in</div>
<div className="animate-enter">Enter with scale</div>
<div className="animate-sweep">Sweep from left</div>
<div className="animate-glow-pulse">Glow pulse</div>
```
