# Panato Employee Management Sidebar Design

## Overview
This document outlines the design and implementation of the Panato employee management sidebar component, featuring a comprehensive self-service interface for employees.

## Component Structure

### 1. Sidebar Layout (`_employee_sidebar.html`)
```
┌─────────────────────────────────┐
│ Profile Section                 │
│ ┌─────────────────────────────┐ │
│ │ [Avatar] Name               │ │
│ │          ID: EMP001         │ │
│ │          Department         │ │
│ │          [Status: Active]   │ │
│ └─────────────────────────────┘ │
│ [Profile] [Notifications]       │
├─────────────────────────────────┤
│ 🕌 ZAKAT CALCULATOR            │
│ ┌─────────────────────────────┐ │
│ │ [💝] احسب زكاة راتبك    [>] │ │
│ │ آخر حساب: يناير 2024        │ │
│ │ المبلغ: 1,250 ل.س           │ │
│ └─────────────────────────────┘ │
├─────────────────────────────────┤
│ 👤 الملف الشخصي               │
│ • البيانات الشخصية             │
│ • معلومات الاتصال              │
│ • جهة الاتصال الطارئ           │
├─────────────────────────────────┤
│ 📅 إدارة الإجازات              │
│ • طلب إجازة جديد               │
│ • تاريخ الإجازات [3]           │
│ • رصيد الإجازات                │
├─────────────────────────────────┤
│ 💰 مراجعة الراتب               │
│ • الراتب الحالي                │
│ • تاريخ الرواتب                │
│ • قسائم الراتب                 │
│ • المستندات الضريبية           │
├─────────────────────────────────┤
│ ⚙️ خدمات إضافية               │
│ • سجل الحضور                   │
│ • تقييم الأداء                 │
│ • التدريب والتطوير             │
├─────────────────────────────────┤
│ Footer Stats & Actions          │
│ أيام العمل: 22 | ساعات: 176    │
│ [Settings] [Help]               │
│ [🚪 تسجيل الخروج]              │
└─────────────────────────────────┘
```

### 2. Key Features

#### A. Zakat Calculator (Prominent Position)
- **Location**: Second section after profile, highly visible
- **Design**: Large, colorful button with Islamic iconography
- **Functionality**: 
  - Auto-calculates based on current salary
  - Shows last calculation date and amount
  - Modal popup with detailed calculation
  - Save calculation history

#### B. Personal Profile Section
- **Authentication**: Employee can only view/edit their own data
- **Information Displayed**:
  - Full name, employee ID, department
  - Contact information
  - Employment status and hire date
  - Emergency contact details
- **Privacy**: Secure access with proper authentication checks

#### C. Leave Management
- **Submit Leave**: Comprehensive form with:
  - Leave type selection (annual, sick, emergency, etc.)
  - Date range picker with validation
  - Reason text area
  - File attachment support
  - Replacement confirmation checkbox
- **Leave History**: 
  - Timeline view of all requests
  - Status indicators (pending, approved, rejected)
  - Filter by status and date
  - Edit pending requests
- **Leave Balance**: 
  - Visual progress bars for each leave type
  - Used vs. available days
  - Annual reset tracking

#### D. Salary Review
- **Current Salary**: 
  - Main salary display with privacy indicators
  - Breakdown of components (basic, allowances, etc.)
  - Next payment date
- **Salary History**: 
  - Timeline of past payments
  - Payment method and dates
  - Year-based filtering
- **Payslips**: 
  - Grid view of available payslips
  - Download individual or bulk PDFs
  - Detailed breakdown view
- **Tax Documents**: 
  - Annual tax statements
  - Downloadable certificates

### 3. Technical Implementation

#### A. Responsive Design
```css
/* Desktop: Full sidebar (320px) */
@media (min-width: 769px) {
    .employee-sidebar { width: 320px; }
}

/* Tablet: Collapsed sidebar (80px) */
@media (max-width: 768px) {
    .employee-sidebar { width: 80px; }
    .sidebar-text { display: none; }
}

/* Mobile: Overlay sidebar */
@media (max-width: 480px) {
    .employee-sidebar { 
        transform: translateX(100%);
        width: 100%;
    }
    .employee-sidebar.active {
        transform: translateX(0);
    }
}
```

#### B. Authentication & Security
- Employee data is filtered by `request.user.employee_profile`
- Salary information includes privacy indicators
- CSRF protection on all forms
- Secure file upload handling
- Session-based authentication

#### C. JavaScript Functionality
- **PanatoEmployeeSidebar Class**: Main controller
- **Section Navigation**: Hash-based routing
- **Zakat Calculator**: Real-time calculations
- **Form Validation**: Client-side validation
- **File Upload**: Drag-and-drop support
- **Responsive Behavior**: Mobile-first approach

### 4. Visual Hierarchy

#### A. Color Scheme (Panato Brand)
- **Primary**: #2563eb (Panato Blue)
- **Secondary**: #1e40af (Dark Blue)
- **Accent**: #3b82f6 (Light Blue)
- **Success**: #10b981 (Green)
- **Warning**: #f59e0b (Orange - for Zakat)
- **Danger**: #ef4444 (Red)

#### B. Typography
- **Headers**: 18-24px, weight 600
- **Body**: 14-16px, weight 400-500
- **Labels**: 14px, weight 500
- **Captions**: 12px, weight 400

#### C. Spacing System
- **Base unit**: 8px
- **Small**: 8px, 12px
- **Medium**: 16px, 20px, 24px
- **Large**: 32px, 40px, 48px

### 5. User Experience Flow

#### A. Navigation Flow
1. **Login** → Employee Dashboard
2. **Sidebar Navigation** → Content sections update
3. **Deep Linking** → URL hash updates
4. **Mobile** → Overlay behavior

#### B. Zakat Calculator Flow
1. **Click Zakat Button** → Modal opens
2. **Auto-populate** → Current salary data
3. **Calculate** → Real-time results
4. **Save** → Store calculation history
5. **Close** → Return to sidebar

#### C. Leave Request Flow
1. **Select Leave Type** → Form updates
2. **Choose Dates** → Validation checks
3. **Enter Reason** → Required field
4. **Attach Files** → Optional documents
5. **Submit** → Server validation
6. **Confirmation** → Success message

### 6. Accessibility Features
- **Keyboard Navigation**: Tab order and focus states
- **Screen Reader Support**: ARIA labels and roles
- **High Contrast**: Alternative color schemes
- **Reduced Motion**: Respects user preferences
- **Focus Indicators**: Clear visual feedback

### 7. Performance Considerations
- **Lazy Loading**: Content sections load on demand
- **Caching**: User preferences stored locally
- **Optimized Images**: Compressed avatars and icons
- **Minimal JavaScript**: Essential functionality only
- **CSS Grid/Flexbox**: Modern layout techniques

### 8. Integration Points
- **Django Authentication**: User and Employee models
- **Vacation System**: Leave request processing
- **Payroll System**: Salary and payslip data
- **File Storage**: Document upload handling
- **Notification System**: Real-time updates

This sidebar design provides a comprehensive, user-friendly interface that prioritizes the zakat calculator while maintaining easy access to all essential employee functions.