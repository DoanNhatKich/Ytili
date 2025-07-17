import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  QrCode, 
  Clock, 
  CheckCircle, 
  XCircle, 
  Copy,
  RefreshCw,
  CreditCard,
  AlertTriangle
} from 'lucide-react';

interface VietQRPaymentData {
  payment_id: string;
  payment_reference: string;
  qr_code: string;
  qr_data_url: string;
  amount: number;
  currency: string;
  bank_info: {
    bank_id: string;
    account_number: string;
    account_name: string;
  };
  expires_at: string;
  instructions: {
    vi: string;
    en: string;
  };
}

interface VietQRPaymentProps {
  donationId: string;
  amount: number;
  description: string;
  onPaymentSuccess?: (paymentReference: string) => void;
  onPaymentCancel?: () => void;
}

export const VietQRPayment: React.FC<VietQRPaymentProps> = ({
  donationId,
  amount,
  description,
  onPaymentSuccess,
  onPaymentCancel
}) => {
  const [paymentData, setPaymentData] = useState<VietQRPaymentData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<'pending' | 'paid' | 'expired' | 'cancelled'>('pending');
  const [bankTransactionId, setBankTransactionId] = useState('');
  const [timeLeft, setTimeLeft] = useState<number>(0);

  useEffect(() => {
    if (paymentData) {
      const expiryTime = new Date(paymentData.expires_at).getTime();
      const updateTimer = () => {
        const now = Date.now();
        const remaining = Math.max(0, expiryTime - now);
        setTimeLeft(remaining);
        
        if (remaining === 0 && paymentStatus === 'pending') {
          setPaymentStatus('expired');
        }
      };

      updateTimer();
      const interval = setInterval(updateTimer, 1000);
      return () => clearInterval(interval);
    }
  }, [paymentData, paymentStatus]);

  const createPayment = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/vietqr-payments/create-qr', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          donation_id: donationId,
          amount: amount,
          description: description,
          expires_in_minutes: 30
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create payment');
      }

      const result = await response.json();
      setPaymentData(result.data);
      setPaymentStatus('pending');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const verifyPayment = async () => {
    if (!paymentData || !bankTransactionId.trim()) {
      setError('Please enter bank transaction ID');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/vietqr-payments/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          payment_reference: paymentData.payment_reference,
          bank_transaction_id: bankTransactionId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Payment verification failed');
      }

      const result = await response.json();
      
      if (result.data.status === 'paid') {
        setPaymentStatus('paid');
        onPaymentSuccess?.(paymentData.payment_reference);
      } else {
        setError('Payment not confirmed by bank');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const cancelPayment = async () => {
    if (!paymentData) return;

    try {
      setLoading(true);
      const response = await fetch(`/api/vietqr-payments/cancel/${paymentData.payment_reference}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (response.ok) {
        setPaymentStatus('cancelled');
        onPaymentCancel?.();
      }
    } catch (err) {
      console.error('Failed to cancel payment:', err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const formatTime = (milliseconds: number) => {
    const minutes = Math.floor(milliseconds / 60000);
    const seconds = Math.floor((milliseconds % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  };

  if (!paymentData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <QrCode className="h-5 w-5" />
            VietQR Payment
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label>Amount</Label>
              <div className="text-2xl font-bold text-green-600">
                {formatAmount(amount)}
              </div>
            </div>
            
            <div>
              <Label>Description</Label>
              <div className="text-gray-600">{description}</div>
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button 
              onClick={createPayment} 
              disabled={loading}
              className="w-full"
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Creating Payment...
                </>
              ) : (
                <>
                  <QrCode className="h-4 w-4 mr-2" />
                  Generate VietQR Code
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Payment Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <QrCode className="h-5 w-5" />
              VietQR Payment
            </div>
            <Badge variant={
              paymentStatus === 'paid' ? 'default' :
              paymentStatus === 'expired' ? 'destructive' :
              paymentStatus === 'cancelled' ? 'secondary' : 'outline'
            }>
              {paymentStatus === 'paid' ? 'Paid' :
               paymentStatus === 'expired' ? 'Expired' :
               paymentStatus === 'cancelled' ? 'Cancelled' : 'Pending'}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {paymentStatus === 'pending' && timeLeft > 0 && (
            <div className="flex items-center gap-2 text-orange-600 mb-4">
              <Clock className="h-4 w-4" />
              <span>Expires in: {formatTime(timeLeft)}</span>
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-6">
            {/* QR Code */}
            <div className="text-center">
              <div className="bg-white p-4 rounded-lg border inline-block">
                <img 
                  src={paymentData.qr_data_url} 
                  alt="VietQR Code"
                  className="w-48 h-48 mx-auto"
                />
              </div>
              <div className="mt-2 text-sm text-gray-600">
                {paymentData.instructions.vi}
              </div>
            </div>

            {/* Payment Details */}
            <div className="space-y-4">
              <div>
                <Label>Amount</Label>
                <div className="text-2xl font-bold text-green-600">
                  {formatAmount(paymentData.amount)}
                </div>
              </div>

              <div>
                <Label>Bank Information</Label>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Bank:</span>
                    <span className="font-medium">{paymentData.bank_info.bank_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Account:</span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono">{paymentData.bank_info.account_number}</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => copyToClipboard(paymentData.bank_info.account_number)}
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                  <div className="flex justify-between">
                    <span>Name:</span>
                    <span className="font-medium">{paymentData.bank_info.account_name}</span>
                  </div>
                </div>
              </div>

              <div>
                <Label>Payment Reference</Label>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm">{paymentData.payment_reference}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => copyToClipboard(paymentData.payment_reference)}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Payment Verification */}
      {paymentStatus === 'pending' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Verify Payment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label htmlFor="bankTransactionId">Bank Transaction ID</Label>
                <Input
                  id="bankTransactionId"
                  value={bankTransactionId}
                  onChange={(e) => setBankTransactionId(e.target.value)}
                  placeholder="Enter transaction ID from your banking app"
                />
                <div className="text-xs text-gray-500 mt-1">
                  After completing payment, enter the transaction ID from your banking app
                </div>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="flex gap-2">
                <Button 
                  onClick={verifyPayment}
                  disabled={loading || !bankTransactionId.trim()}
                  className="flex-1"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Verify Payment
                    </>
                  )}
                </Button>
                
                <Button 
                  onClick={cancelPayment}
                  variant="outline"
                  disabled={loading}
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Success Message */}
      {paymentStatus === 'paid' && (
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>
            Payment verified successfully! Your donation has been confirmed and recorded on the blockchain.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};
