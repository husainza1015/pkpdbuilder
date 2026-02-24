/**
 * Shared types for PKPDBuilder
 * Author: Husain Z Attarwala, PhD
 */

export interface Tool {
  name: string;
  description: string;
  parameters?: {
    type: 'object';
    properties: Record<string, any>;
    required?: string[];
  };
  input_schema?: {
    type: 'object';
    properties: Record<string, any>;
    required?: string[];
  };
}
