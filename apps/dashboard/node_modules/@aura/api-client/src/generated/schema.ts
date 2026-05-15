// AUTO-GENERATED from openapi.json — run `pnpm generate:api` to regenerate.
// Replace openapi.json with ../../../aura-id/shared/openapi.json when backend is ready.

export interface paths {
  '/scans': {
    post: operations['createScan'];
  };
  '/scans/{id}': {
    get: operations['getScan'];
    patch: operations['updateScan'];
  };
  '/hotels/me': {
    get: operations['getMyHotel'];
  };
}

export interface components {
  schemas: {
    Scan: {
      id: string;
      status: 'pending' | 'processing' | 'complete' | 'failed';
      extractedFields?: components['schemas']['ExtractedFields'];
    };
    ExtractedFields: {
      fullName?: string;
      dateOfBirth?: string;
      documentNumber?: string;
      address?: string;
    };
    Hotel: {
      id: string;
      name: string;
      imageRetentionHours: number;
    };
  };
}

export interface operations {
  createScan: {
    requestBody: {
      content: {
        'multipart/form-data': {
          image: Blob;
          hotelId: string;
        };
      };
    };
    responses: {
      202: {
        content: {
          'application/json': components['schemas']['Scan'];
        };
      };
    };
  };
  getScan: {
    parameters: { path: { id: string } };
    responses: {
      200: { content: { 'application/json': components['schemas']['Scan'] } };
    };
  };
  updateScan: {
    parameters: { path: { id: string } };
    requestBody: {
      content: { 'application/json': components['schemas']['ExtractedFields'] };
    };
    responses: {
      200: { content: { 'application/json': components['schemas']['Scan'] } };
    };
  };
  getMyHotel: {
    responses: {
      200: { content: { 'application/json': components['schemas']['Hotel'] } };
    };
  };
}
