import { MongoClient, ObjectId, Binary } from 'mongodb';
import crypto from 'crypto';

// Define types for extracted information
interface ExtractedInfo {
  // Personal Information
  firstName?: string;
  lastName?: string;
  dateOfBirth?: string;
  ssn?: string;
  email?: string;
  phone?: string;

  // Address Information
  address?: {
    street?: string;
    city?: string;
    state?: string;
    zipCode?: string;
  };

  // Financial Information
  income?: {
    annual?: number;
    type?: string;  // e.g., 'salary', 'self-employed'
    employer?: string;
  };

  // Tax Information
  taxInfo?: {
    year?: number;
    filingStatus?: string;
    w2Income?: number;
    deductions?: number;
  };

  // Insurance Information
  insurance?: {
    provider?: string;
    policyNumber?: string;
    coverage?: string;
  };

  // Document-specific fields can be added as needed
  [key: string]: any;
}

export class MongoDocumentService {
  private client: MongoClient;
  private encryptionKey: Buffer;
  private isConnected: boolean = false;

  constructor() {
    this.client = new MongoClient('mongodb://localhost:27017');
    this.encryptionKey = crypto.scryptSync(process.env.ENCRYPTION_KEY || 'your-secure-key', 'salt', 32);
  }

  async connect() {
    if (!this.isConnected) {
      await this.client.connect();
      this.isConnected = true;
      console.log('Connected to MongoDB');
    }
  }

  private encrypt(buffer: Buffer): { encrypted: Buffer; iv: Buffer; authTag: Buffer } {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-gcm', this.encryptionKey, iv);
    const encrypted = Buffer.concat([cipher.update(buffer), cipher.final()]);
    const authTag = cipher.getAuthTag();
    
    return { 
      encrypted: Buffer.from(encrypted), 
      iv: Buffer.from(iv), 
      authTag: Buffer.from(authTag) 
    };
  }

  private decrypt(encrypted: Buffer | Binary, iv: Buffer | Binary, authTag: Buffer | Binary): Buffer {
    // Convert MongoDB Binary types to Buffers if needed
    const encryptedBuffer = Buffer.isBuffer(encrypted) ? encrypted : Buffer.from(encrypted.buffer);
    const ivBuffer = Buffer.isBuffer(iv) ? iv : Buffer.from(iv.buffer);
    const authTagBuffer = Buffer.isBuffer(authTag) ? authTag : Buffer.from(authTag.buffer);

    const decipher = crypto.createDecipheriv('aes-256-gcm', this.encryptionKey, ivBuffer);
    decipher.setAuthTag(authTagBuffer);
    
    return Buffer.concat([decipher.update(encryptedBuffer), decipher.final()]);
  }

  async saveDocument(name: string, content: Buffer, metadata: any, extractedInfo?: ExtractedInfo) {
    await this.connect();

    const { encrypted, iv, authTag } = this.encrypt(content);
    
    const doc = {
      name,
      content: new Binary(encrypted),
      iv: new Binary(iv),
      authTag: new Binary(authTag),
      metadata: {
        ...metadata,
        createdAt: new Date(),
        lastModified: new Date()
      },
      extractedInfo: extractedInfo || {},  // Store extracted information
      extractionHistory: [{  // Keep track of information updates
        timestamp: new Date(),
        fields: Object.keys(extractedInfo || {}),
        source: 'initial_upload'
      }]
    };

    const result = await this.client
      .db('quill')
      .collection('documents')
      .insertOne(doc);

    return { 
      _id: result.insertedId.toString(),
      name,
      metadata: metadata,
      extractedInfo: doc.extractedInfo
    };
  }

  async getDocument(id: string) {
    await this.connect();

    const doc = await this.client
      .db('quill')
      .collection('documents')
      .findOne({ _id: new ObjectId(id) });

    if (!doc) {
      throw new Error('Document not found');
    }

    try {
      const decrypted = this.decrypt(doc.content, doc.iv, doc.authTag);

      return {
        _id: doc._id.toString(),
        name: doc.name,
        content: decrypted,
        metadata: doc.metadata,
        extractedInfo: doc.extractedInfo
      };
    } catch (error) {
      console.error('Decryption error:', {
        hasContent: !!doc.content,
        hasIV: !!doc.iv,
        hasAuthTag: !!doc.authTag,
        contentType: doc.content?.constructor.name,
        ivType: doc.iv?.constructor.name,
        authTagType: doc.authTag?.constructor.name
      });
      throw error;
    }
  }

  async deleteDocument(id: string) {
    await this.connect();

    const result = await this.client
      .db('quill')
      .collection('documents')
      .deleteOne({ _id: new ObjectId(id) });

    if (result.deletedCount === 0) {
      throw new Error('Document not found');
    }

    return true;
  }

  async listDocuments() {
    await this.connect();

    const documents = await this.client
      .db('quill')
      .collection('documents')
      .find({}, { projection: { content: 0, iv: 0, authTag: 0 } })
      .toArray();

    return documents.map(doc => ({
      ...doc,
      _id: doc._id.toString()
    }));
  }

  async updateExtractedInfo(id: string, newInfo: Partial<ExtractedInfo>, source: string = 'manual_update') {
    await this.connect();

    const result = await this.client
      .db('quill')
      .collection('documents')
      .updateOne(
        { _id: new ObjectId(id) },
        {
          $set: { 
            'extractedInfo': newInfo,
            'metadata.lastModified': new Date()
          },
          $push: {
            'extractionHistory': {
              timestamp: new Date(),
              fields: Object.keys(newInfo),
              source: source
            }
          }
        }
      );

    if (result.modifiedCount === 0) {
      throw new Error('Document not found or no changes made');
    }

    return true;
  }

  async getExtractedInfo(id: string) {
    await this.connect();

    const doc = await this.client
      .db('quill')
      .collection('documents')
      .findOne(
        { _id: new ObjectId(id) },
        { projection: { extractedInfo: 1, extractionHistory: 1 } }
      );

    if (!doc) {
      throw new Error('Document not found');
    }

    return {
      extractedInfo: doc.extractedInfo,
      extractionHistory: doc.extractionHistory
    };
  }

  async searchByExtractedInfo(query: Partial<ExtractedInfo>) {
    await this.connect();

    const searchQuery = Object.entries(query).reduce((acc, [key, value]) => {
      acc[`extractedInfo.${key}`] = value;
      return acc;
    }, {} as any);

    const documents = await this.client
      .db('quill')
      .collection('documents')
      .find(searchQuery)
      .project({ content: 0, iv: 0, authTag: 0 })
      .toArray();

    return documents.map(doc => ({
      ...doc,
      _id: doc._id.toString()
    }));
  }

  async getInformationSummary() {
    await this.connect();

    const documents = await this.client
      .db('quill')
      .collection('documents')
      .find({})
      .project({ 
        extractedInfo: 1, 
        name: 1, 
        'metadata.createdAt': 1 
      })
      .toArray();

    // Combine and organize information from all documents
    return documents.reduce((summary, doc) => {
      const info = doc.extractedInfo;
      if (info) {
        Object.entries(info).forEach(([key, value]) => {
          if (!summary[key]) {
            summary[key] = {
              value,
              sources: [{ 
                documentId: doc._id,
                documentName: doc.name,
                date: doc.metadata.createdAt
              }]
            };
          } else {
            summary[key].sources.push({
              documentId: doc._id,
              documentName: doc.name,
              date: doc.metadata.createdAt
            });
          }
        });
      }
      return summary;
    }, {} as any);
  }
}