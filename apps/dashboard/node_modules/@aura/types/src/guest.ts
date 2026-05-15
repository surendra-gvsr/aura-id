export interface Guest {
  id: string;
  hotelId: string;
  fullName: string;
  dateOfBirth: string;
  documentNumber: string;
  address?: string;
  createdAt: string;
  imageDeletedAt?: string;
}
