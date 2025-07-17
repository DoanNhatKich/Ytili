/**
 * Donation Advisory Dashboard Component
 * Provides personalized donation recommendations and budget planning
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Heart, DollarSign, MapPin, TrendingUp, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

interface DonationRecommendation {
  type: string;
  title: string;
  description: string;
  data: {
    campaign_id?: number;
    campaign_title?: string;
    suggested_amount?: number;
    campaign_goal?: number;
    current_amount?: number;
    urgency?: string;
    amount?: number;
    currency?: string;
    impact_description?: string;
  };
  confidence: number;
}

interface BudgetRange {
  min: number;
  max: number;
  recommended: number[];
}

interface DonationAdvisoryProps {
  apiBaseUrl?: string;
  authToken?: string;
  onDonationSelect?: (recommendation: DonationRecommendation) => void;
  className?: string;
}

export const DonationAdvisory: React.FC<DonationAdvisoryProps> = ({
  apiBaseUrl = '/api/v1',
  authToken,
  onDonationSelect,
  className = ''
}) => {
  const [recommendations, setRecommendations] = useState<DonationRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [budgetAmount, setBudgetAmount] = useState<number>(0);
  const [budgetRange, setBudgetRange] = useState<string>('medium');
  const [medicalInterests, setMedicalInterests] = useState<string[]>([]);
  const [locationPreference, setLocationPreference] = useState<string>('');
  
  const budgetRanges: Record<string, BudgetRange> = {
    low: { min: 50000, max: 500000, recommended: [100000, 200000, 300000] },
    medium: { min: 500000, max: 2000000, recommended: [750000, 1000000, 1500000] },
    high: { min: 2000000, max: 10000000, recommended: [3000000, 5000000, 7000000] },
    premium: { min: 10000000, max: 100000000, recommended: [15000000, 25000000, 50000000] }
  };
  
  const medicalSpecialties = [
    { id: 'cardiology', name: 'Tim mạch', icon: '❤️' },
    { id: 'oncology', name: 'Ung thư', icon: '🎗️' },
    { id: 'pediatrics', name: 'Nhi khoa', icon: '👶' },
    { id: 'neurology', name: 'Thần kinh', icon: '🧠' },
    { id: 'orthopedics', name: 'Xương khớp', icon: '🦴' },
    { id: 'emergency', name: 'Cấp cứu', icon: '🚨' },
    { id: 'surgery', name: 'Phẫu thuật', icon: '⚕️' },
    { id: 'dialysis', name: 'Thận', icon: '🫘' }
  ];
  
  const vietnamProvinces = [
    'Hà Nội', 'TP.HCM', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ',
    'An Giang', 'Bà Rịa - Vũng Tàu', 'Bắc Giang', 'Bắc Kạn', 'Bạc Liêu',
    'Bắc Ninh', 'Bến Tre', 'Bình Định', 'Bình Dương', 'Bình Phước',
    'Bình Thuận', 'Cà Mau', 'Cao Bằng', 'Đắk Lắk', 'Đắk Nông'
  ];
  
  // Get donation recommendations
  const getDonationRecommendations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${apiBaseUrl}/ai-agent/donation-advice`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken && { 'Authorization': `Bearer ${authToken}` })
        },
        body: JSON.stringify({
          budget_amount: budgetAmount || null,
          budget_range: budgetRange,
          medical_interests: medicalInterests,
          location_preference: locationPreference || null
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to get donation recommendations');
      }
      
      const data = await response.json();
      
      if (data.success) {
        setRecommendations(data.recommendations || []);
      } else {
        throw new Error(data.error || 'Unknown error');
      }
    } catch (err) {
      setError('Không thể lấy gợi ý quyên góp');
      console.error('Failed to get donation recommendations:', err);
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl, authToken, budgetAmount, budgetRange, medicalInterests, locationPreference]);
  
  // Handle medical interest toggle
  const toggleMedicalInterest = useCallback((specialty: string) => {
    setMedicalInterests(prev => 
      prev.includes(specialty)
        ? prev.filter(s => s !== specialty)
        : [...prev, specialty]
    );
  }, []);
  
  // Format currency
  const formatCurrency = useCallback((amount: number) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  }, []);
  
  // Get urgency color
  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical':
        return 'text-red-600 bg-red-100';
      case 'high':
        return 'text-orange-600 bg-orange-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-green-600 bg-green-100';
    }
  };
  
  // Get urgency icon
  const getUrgencyIcon = (urgency: string) => {
    switch (urgency) {
      case 'critical':
        return <AlertTriangle className="w-4 h-4" />;
      case 'high':
        return <Clock className="w-4 h-4" />;
      default:
        return <CheckCircle className="w-4 h-4" />;
    }
  };
  
  // Calculate progress percentage
  const calculateProgress = (current: number, goal: number) => {
    return Math.min((current / goal) * 100, 100);
  };
  
  useEffect(() => {
    getDonationRecommendations();
  }, [getDonationRecommendations]);
  
  return (
    <div className={`bg-white rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <Heart className="w-8 h-8 text-red-500" />
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Tư Vấn Quyên Góp AI</h2>
            <p className="text-gray-600">Nhận gợi ý quyên góp phù hợp với ngân sách và sở thích của bạn</p>
          </div>
        </div>
      </div>
      
      {/* Configuration Panel */}
      <div className="p-6 border-b border-gray-200 bg-gray-50">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Thiết Lập Tùy Chọn</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Budget Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Ngân sách cụ thể (VND)
            </label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="number"
                value={budgetAmount || ''}
                onChange={(e) => setBudgetAmount(Number(e.target.value))}
                placeholder="Nhập số tiền"
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          
          {/* Budget Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Mức ngân sách
            </label>
            <select
              value={budgetRange}
              onChange={(e) => setBudgetRange(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="low">Thấp (50K - 500K)</option>
              <option value="medium">Trung bình (500K - 2M)</option>
              <option value="high">Cao (2M - 10M)</option>
              <option value="premium">Rất cao (10M+)</option>
            </select>
          </div>
          
          {/* Location Preference */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Khu vực ưu tiên
            </label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <select
                value={locationPreference}
                onChange={(e) => setLocationPreference(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Tất cả khu vực</option>
                {vietnamProvinces.map(province => (
                  <option key={province} value={province}>{province}</option>
                ))}
              </select>
            </div>
          </div>
          
          {/* Update Button */}
          <div className="flex items-end">
            <button
              onClick={getDonationRecommendations}
              disabled={isLoading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Đang tải...' : 'Cập nhật gợi ý'}
            </button>
          </div>
        </div>
        
        {/* Medical Interests */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Lĩnh vực y tế quan tâm
          </label>
          <div className="flex flex-wrap gap-2">
            {medicalSpecialties.map(specialty => (
              <button
                key={specialty.id}
                onClick={() => toggleMedicalInterest(specialty.id)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  medicalInterests.includes(specialty.id)
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                <span className="mr-1">{specialty.icon}</span>
                {specialty.name}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 border-l-4 border-red-400">
          <div className="flex items-center">
            <AlertTriangle className="w-5 h-5 text-red-400 mr-2" />
            <p className="text-red-700">{error}</p>
          </div>
        </div>
      )}
      
      {/* Recommendations */}
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Gợi Ý Quyên Góp</h3>
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-green-500" />
            <span className="text-sm text-gray-600">{recommendations.length} gợi ý</span>
          </div>
        </div>
        
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : recommendations.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Heart className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>Chưa có gợi ý quyên góp. Vui lòng điều chỉnh tùy chọn và thử lại.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.map((rec, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => onDonationSelect?.(rec)}
              >
                <div className="flex items-start justify-between mb-3">
                  <h4 className="font-semibold text-gray-900 flex-1">{rec.title}</h4>
                  {rec.data.urgency && (
                    <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${getUrgencyColor(rec.data.urgency)}`}>
                      {getUrgencyIcon(rec.data.urgency)}
                      <span className="capitalize">{rec.data.urgency}</span>
                    </span>
                  )}
                </div>
                
                <p className="text-gray-600 text-sm mb-3">{rec.description}</p>
                
                {rec.type === 'campaign_match' && rec.data.campaign_goal && (
                  <div className="mb-3">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>Tiến độ</span>
                      <span>
                        {formatCurrency(rec.data.current_amount || 0)} / {formatCurrency(rec.data.campaign_goal)}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${calculateProgress(rec.data.current_amount || 0, rec.data.campaign_goal)}%`
                        }}
                      ></div>
                    </div>
                  </div>
                )}
                
                {rec.data.suggested_amount && (
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-blue-600">
                      {formatCurrency(rec.data.suggested_amount)}
                    </span>
                    <span className="text-sm text-gray-500">
                      Độ tin cậy: {Math.round(rec.confidence * 100)}%
                    </span>
                  </div>
                )}
                
                {rec.data.impact_description && (
                  <p className="text-xs text-gray-500 mt-2 italic">
                    💡 {rec.data.impact_description}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DonationAdvisory;
