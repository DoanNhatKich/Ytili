import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Shield, 
  CheckCircle, 
  AlertTriangle, 
  Clock, 
  ExternalLink,
  Blockchain,
  TrendingUp
} from 'lucide-react';

interface TransparencyData {
  donationId: string;
  transparencyScore: number;
  isVerified: boolean;
  totalTransactions: number;
  brokenLinks: number;
  invalidHashes: number;
  verifiedAt: string;
  blockchainHash?: string;
}

interface TransparencyDashboardProps {
  donationId: string;
}

export const TransparencyDashboard: React.FC<TransparencyDashboardProps> = ({ 
  donationId 
}) => {
  const [transparencyData, setTransparencyData] = useState<TransparencyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTransparencyData();
  }, [donationId]);

  const fetchTransparencyData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/blockchain/transparency/${donationId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch transparency data');
      }

      const data = await response.json();
      setTransparencyData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBadgeVariant = (score: number) => {
    if (score >= 80) return 'default';
    if (score >= 60) return 'secondary';
    return 'destructive';
  };

  const openBlockchainExplorer = () => {
    if (transparencyData?.blockchainHash) {
      // Open Saga blockchain explorer
      window.open(
        `https://explorer.saga.io/tx/${transparencyData.blockchainHash}`,
        '_blank'
      );
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Transparency Dashboard
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Transparency Dashboard
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-4 w-4" />
            <span>{error}</span>
          </div>
          <Button 
            onClick={fetchTransparencyData} 
            variant="outline" 
            className="mt-4"
          >
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!transparencyData) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Main Transparency Score */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Transparency Score
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className={`text-4xl font-bold ${getScoreColor(transparencyData.transparencyScore)}`}>
                {transparencyData.transparencyScore}
              </div>
              <div className="text-gray-500">/ 100</div>
            </div>
            <Badge variant={getScoreBadgeVariant(transparencyData.transparencyScore)}>
              {transparencyData.transparencyScore >= 80 ? 'Excellent' :
               transparencyData.transparencyScore >= 60 ? 'Good' : 'Needs Improvement'}
            </Badge>
          </div>
          
          <Progress 
            value={transparencyData.transparencyScore} 
            className="mb-4"
          />
          
          <div className="flex items-center gap-2 text-sm text-gray-600">
            {transparencyData.isVerified ? (
              <>
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span>Verified on blockchain</span>
              </>
            ) : (
              <>
                <Clock className="h-4 w-4 text-yellow-600" />
                <span>Pending verification</span>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Transaction Details */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Blockchain className="h-5 w-5" />
            Blockchain Details
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {transparencyData.totalTransactions}
              </div>
              <div className="text-sm text-gray-600">Total Transactions</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {transparencyData.totalTransactions - transparencyData.brokenLinks}
              </div>
              <div className="text-sm text-gray-600">Valid Links</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {transparencyData.brokenLinks}
              </div>
              <div className="text-sm text-gray-600">Broken Links</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {transparencyData.invalidHashes}
              </div>
              <div className="text-sm text-gray-600">Invalid Hashes</div>
            </div>
          </div>

          {transparencyData.blockchainHash && (
            <div className="border-t pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Blockchain Transaction</div>
                  <div className="text-sm text-gray-600 font-mono">
                    {transparencyData.blockchainHash.slice(0, 20)}...
                  </div>
                </div>
                <Button 
                  onClick={openBlockchainExplorer}
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  View on Explorer
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Contract Addresses */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Smart Contract Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <div className="text-sm font-medium text-gray-700">Donation Registry</div>
              <div className="text-xs font-mono text-gray-600 bg-gray-50 p-2 rounded">
                0x96c394B6B709Ac81a3Eef1c1B94ceB4372bBE487
              </div>
            </div>
            
            <div>
              <div className="text-sm font-medium text-gray-700">Transparency Verifier</div>
              <div className="text-xs font-mono text-gray-600 bg-gray-50 p-2 rounded">
                0x4c25ECb2cB57A1188218499c0C20EDFB426385a0
              </div>
            </div>
            
            <div>
              <div className="text-sm font-medium text-gray-700">YTILI Token</div>
              <div className="text-xs font-mono text-gray-600 bg-gray-50 p-2 rounded">
                0x66C06efE9B8B44940379F5c53328a35a3Abc3Fe7
              </div>
            </div>
          </div>
          
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <div className="text-sm text-blue-800">
              <strong>Network:</strong> Saga Blockchain (Chain ID: 2752546100676000)
            </div>
            <div className="text-xs text-blue-600 mt-1">
              All transactions are recorded on the Saga blockchain for maximum transparency
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Verification Status */}
      {transparencyData.verifiedAt && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Verification History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-gray-600">
              Last verified: {new Date(transparencyData.verifiedAt).toLocaleString()}
            </div>
            <Button 
              onClick={fetchTransparencyData}
              variant="outline"
              size="sm"
              className="mt-2"
            >
              Refresh Verification
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
