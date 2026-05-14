export type ScanStatus = 'pending' | 'processing' | 'complete' | 'failed';

export interface ExtractedFields {
  fullName?: string;
  dateOfBirth?: string;
  documentNumber?: string;
  address?: string;
  documentType?: string;
  expiryDate?: string;
}

export interface Scan {
  id: string;
  hotelId: string;
  status: ScanStatus;
  createdAt: string;
  extractedFields?: ExtractedFields;
}
