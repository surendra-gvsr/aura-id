'use client';

// ConfirmForm: Renders editable text fields extracted from an ID scan.
// NO image, video, or image URL is rendered here — only text values.

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button, Input, Label } from '@aura/ui';
import type { ExtractedFields } from '@aura/api-client';

// Validation schema — all required fields except address
const schema = z.object({
  fullName: z.string().min(1, 'Name is required'),
  dateOfBirth: z.string().min(1, 'Date of birth is required'),
  documentNumber: z.string().min(1, 'Document number is required'),
  address: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface ConfirmFormProps {
  initialFields: ExtractedFields;
  onSubmit: (fields: FormValues) => Promise<void>;
  isSubmitting: boolean;
}

export function ConfirmForm({
  initialFields,
  onSubmit,
  isSubmitting,
}: ConfirmFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      fullName: initialFields.fullName ?? '',
      dateOfBirth: initialFields.dateOfBirth ?? '',
      documentNumber: initialFields.documentNumber ?? '',
      address: initialFields.address ?? '',
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="fullName">Full name</Label>
        <Input id="fullName" {...register('fullName')} autoComplete="off" />
        {errors.fullName && (
          <p className="text-xs text-destructive">{errors.fullName.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="dateOfBirth">Date of birth</Label>
        <Input
          id="dateOfBirth"
          {...register('dateOfBirth')}
          autoComplete="off"
        />
        {errors.dateOfBirth && (
          <p className="text-xs text-destructive">
            {errors.dateOfBirth.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="documentNumber">Document number</Label>
        <Input
          id="documentNumber"
          {...register('documentNumber')}
          autoComplete="off"
        />
        {errors.documentNumber && (
          <p className="text-xs text-destructive">
            {errors.documentNumber.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="address">
          Address <span className="text-muted-foreground">(optional)</span>
        </Label>
        <Input id="address" {...register('address')} autoComplete="off" />
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Sending…' : 'Submit to PMS'}
      </Button>
    </form>
  );
}
