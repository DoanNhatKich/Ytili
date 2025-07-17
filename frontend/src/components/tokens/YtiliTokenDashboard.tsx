import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  Coins, 
  TrendingUp, 
  Gift, 
  Award,
  ExternalLink,
  RefreshCw,
  Wallet,
  Star
} from 'lucide-react';

interface TokenData {
  balance: number;
  earned: number;
  redeemed: number;
  votingPower: number;
  tier: string;
  recentTransactions: TokenTransaction[];
}

interface TokenTransaction {
  id: string;
  type: 'earned' | 'redeemed' | 'transferred';
  amount: number;
  reason: string;
  timestamp: string;
  txHash?: string;
}

interface RedemptionOption {
  id: string;
  name: string;
  description: string;
  cost: number;
  category: string;
  available: boolean;
}

export const YtiliTokenDashboard: React.FC = () => {
  const [tokenData, setTokenData] = useState<TokenData | null>(null);
  const [redemptionOptions, setRedemptionOptions] = useState<RedemptionOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTokenData();
    fetchRedemptionOptions();
  }, []);

  const fetchTokenData = async () => {
    try {
      const response = await fetch('/api/tokens/balance', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch token data');
      }

      const data = await response.json();
      setTokenData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const fetchRedemptionOptions = async () => {
    try {
      const response = await fetch('/api/tokens/redemption-options');
      if (response.ok) {
        const data = await response.json();
        setRedemptionOptions(data);
      }
    } catch (err) {
      console.error('Failed to fetch redemption options:', err);
    }
  };

  const redeemTokens = async (optionId: string) => {
    try {
      const response = await fetch('/api/tokens/redeem', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ option_id: optionId })
      });

      if (response.ok) {
        await fetchTokenData(); // Refresh balance
      }
    } catch (err) {
      console.error('Failed to redeem tokens:', err);
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'bronze': return 'text-orange-600';
      case 'silver': return 'text-gray-600';
      case 'gold': return 'text-yellow-600';
      case 'platinum': return 'text-purple-600';
      default: return 'text-gray-600';
    }
  };

  const getTierProgress = (tier: string, earned: number) => {
    const thresholds = {
      bronze: 0,
      silver: 1000,
      gold: 5000,
      platinum: 10000
    };
    
    const currentThreshold = thresholds[tier.toLowerCase() as keyof typeof thresholds] || 0;
    const nextTier = Object.entries(thresholds).find(([_, threshold]) => threshold > earned);
    
    if (!nextTier) return 100;
    
    const nextThreshold = nextTier[1];
    return Math.min(100, (earned / nextThreshold) * 100);
  };

  const formatTokens = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const openBlockchainExplorer = (txHash: string) => {
    window.open(`https://explorer.saga.io/tx/${txHash}`, '_blank');
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <RefreshCw className="h-8 w-8 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  if (error || !tokenData) {
    return (
      <Card>
        <CardContent className="text-center py-8">
          <div className="text-red-600 mb-4">{error || 'No token data available'}</div>
          <Button onClick={fetchTokenData} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Token Balance Overview */}
      <div className="grid md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Coins className="h-5 w-5 text-blue-600" />
              YTILI Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600 mb-2">
              {formatTokens(tokenData.balance)}
            </div>
            <div className="text-sm text-gray-600">
              Available for redemption
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <TrendingUp className="h-5 w-5 text-green-600" />
              Total Earned
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600 mb-2">
              {formatTokens(tokenData.earned)}
            </div>
            <div className="text-sm text-gray-600">
              Lifetime earnings
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Award className="h-5 w-5 text-purple-600" />
              Tier Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold mb-2 ${getTierColor(tokenData.tier)}`}>
              {tokenData.tier}
            </div>
            <Progress 
              value={getTierProgress(tokenData.tier, tokenData.earned)} 
              className="mb-2"
            />
            <div className="text-sm text-gray-600">
              Progress to next tier
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Voting Power */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Star className="h-5 w-5" />
            Governance & Voting
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-purple-600">
                {formatTokens(tokenData.votingPower)}
              </div>
              <div className="text-sm text-gray-600">Voting Power</div>
            </div>
            <Button variant="outline">
              <Star className="h-4 w-4 mr-2" />
              View Proposals
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Redemption Options */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Gift className="h-5 w-5" />
            Redeem Tokens
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {redemptionOptions.map((option) => (
              <div 
                key={option.id}
                className="border rounded-lg p-4 space-y-3"
              >
                <div>
                  <div className="font-medium">{option.name}</div>
                  <div className="text-sm text-gray-600">{option.description}</div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Coins className="h-4 w-4 text-blue-600" />
                    <span className="font-bold">{formatTokens(option.cost)}</span>
                  </div>
                  <Badge variant={option.available ? 'default' : 'secondary'}>
                    {option.category}
                  </Badge>
                </div>
                
                <Button 
                  onClick={() => redeemTokens(option.id)}
                  disabled={!option.available || tokenData.balance < option.cost}
                  className="w-full"
                  size="sm"
                >
                  {tokenData.balance < option.cost ? 'Insufficient Balance' : 'Redeem'}
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Transactions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5" />
            Recent Transactions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {tokenData.recentTransactions.map((tx) => (
              <div 
                key={tx.id}
                className="flex items-center justify-between p-3 border rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-full ${
                    tx.type === 'earned' ? 'bg-green-100 text-green-600' :
                    tx.type === 'redeemed' ? 'bg-red-100 text-red-600' :
                    'bg-blue-100 text-blue-600'
                  }`}>
                    {tx.type === 'earned' ? <TrendingUp className="h-4 w-4" /> :
                     tx.type === 'redeemed' ? <Gift className="h-4 w-4" /> :
                     <Wallet className="h-4 w-4" />}
                  </div>
                  
                  <div>
                    <div className="font-medium">{tx.reason}</div>
                    <div className="text-sm text-gray-600">
                      {new Date(tx.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className={`font-bold ${
                    tx.type === 'earned' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {tx.type === 'earned' ? '+' : '-'}{formatTokens(tx.amount)}
                  </div>
                  
                  {tx.txHash && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openBlockchainExplorer(tx.txHash!)}
                    >
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Contract Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ExternalLink className="h-5 w-5" />
            Token Contract
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Contract Address:</span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm">0x66C06efE9B8B44940379F5c53328a35a3Abc3Fe7</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openBlockchainExplorer('0x66C06efE9B8B44940379F5c53328a35a3Abc3Fe7')}
                >
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Network:</span>
              <span className="text-sm font-medium">Saga Blockchain</span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Token Symbol:</span>
              <span className="text-sm font-medium">YTILI</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
