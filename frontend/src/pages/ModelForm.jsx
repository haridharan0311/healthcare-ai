import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { crudApi, fetchDropdowns } from '../api';

const FORM_FIELDS = {
  clinics: [
    { name: 'clinic_name',      label: 'Clinic name', type: 'text',     required: true },
    { name: 'clinic_address_1', label: 'Address',     type: 'textarea'               },
  ],

  doctors: [
    { name: 'first_name',    label: 'First name',    type: 'text',   required: true },
    { name: 'last_name',     label: 'Last name',     type: 'text'                   },
    { name: 'gender',        label: 'Gender',        type: 'select',
      options: [
        { value: 'M', label: 'Male'    },
        { value: 'F', label: 'Female'  },
        { value: 'O', label: 'Other'   },
        { value: 'U', label: 'Unknown' },
      ]
    },
    { name: 'qualification', label: 'Qualification', type: 'text',   required: true },
    { name: 'clinic',        label: 'Clinic',        type: 'fk', fkModel: 'clinics',  required: true },
  ],

  patients: [
    { name: 'first_name',     label: 'First name',    type: 'text',   required: true },
    { name: 'last_name',      label: 'Last name',     type: 'text',   required: true },
    { name: 'gender',         label: 'Gender',        type: 'select',
      options: [
        { value: 'M', label: 'Male'    },
        { value: 'F', label: 'Female'  },
        { value: 'O', label: 'Other'   },
        { value: 'U', label: 'Unknown' },
      ]
    },
    { name: 'title',          label: 'Title',         type: 'select',
      options: [
        { value: 'Mr',  label: 'Mr'  },
        { value: 'Ms',  label: 'Ms'  },
        { value: 'Mrs', label: 'Mrs' },
        { value: 'Dr',  label: 'Dr'  },
      ]
    },
    { name: 'dob',            label: 'Date of birth', type: 'date'                   },
    { name: 'mobile_number',  label: 'Mobile number', type: 'text'                   },
    { name: 'address_line_1', label: 'Address',       type: 'textarea'               },
    { name: 'clinic',         label: 'Clinic',        type: 'fk', fkModel: 'clinics',  required: true },
    { name: 'doctor',         label: 'Doctor',        type: 'fk', fkModel: 'doctors'               },
  ],

  diseases: [
    { name: 'name',      label: 'Disease name',  type: 'text',   required: true },
    { name: 'season',    label: 'Season',        type: 'select',
      options: [
        { value: 'Summer',  label: 'Summer'      },
        { value: 'Monsoon', label: 'Monsoon'     },
        { value: 'Winter',  label: 'Winter'      },
        { value: 'All',     label: 'All seasons' },
      ]
    },
    { name: 'category',  label: 'Category',      type: 'text'   },
    { name: 'severity',  label: 'Severity (1–5)', type: 'number' },
    { name: 'is_active', label: 'Active',         type: 'checkbox' },
  ],

  appointments: [
    { name: 'op_number',            label: 'OP number',   type: 'text',           required: true },
    { name: 'appointment_datetime', label: 'Date & time', type: 'datetime-local', required: true },
    { name: 'appointment_status',   label: 'Status',      type: 'select',
      options: [
        { value: 'Scheduled', label: 'Scheduled' },
        { value: 'Completed', label: 'Completed' },
        { value: 'Cancelled', label: 'Cancelled' },
      ]
    },
    { name: 'clinic',   label: 'Clinic',   type: 'fk', fkModel: 'clinics',   required: true },
    { name: 'doctor',   label: 'Doctor',   type: 'fk', fkModel: 'doctors',   required: true },
    { name: 'patient',  label: 'Patient',  type: 'fk', fkModel: 'patients',  required: true },
    { name: 'disease',  label: 'Disease',  type: 'fk', fkModel: 'diseases',  required: true },
  ],

  drugs: [
    { name: 'drug_name',     label: 'Drug name',     type: 'text',   required: true },
    { name: 'generic_name',  label: 'Generic name',  type: 'text'                   },
    { name: 'drug_strength', label: 'Strength',      type: 'text'                   },
    { name: 'dosage_type',   label: 'Dosage type',   type: 'text'                   },
    { name: 'current_stock', label: 'Current stock', type: 'number'                 },
    { name: 'clinic',        label: 'Clinic',        type: 'fk', fkModel: 'clinics', required: true },
  ],

  prescriptions: [
    { name: 'prescription_date', label: 'Date',        type: 'date',   required: true },
    { name: 'clinic',       label: 'Clinic',       type: 'fk', fkModel: 'clinics',       required: true },
    { name: 'doctor',       label: 'Doctor',       type: 'fk', fkModel: 'doctors',       required: true },
    { name: 'patient',      label: 'Patient',      type: 'fk', fkModel: 'patients',      required: true },
    { name: 'appointment',  label: 'Appointment',  type: 'fk', fkModel: 'appointments',  required: true },
  ],

  'prescription-lines': [
    { name: 'prescription', label: 'Prescription', type: 'fk', fkModel: 'prescriptions', required: true },
    { name: 'drug',         label: 'Drug',         type: 'fk', fkModel: 'drugs',         required: true },
    { name: 'disease',      label: 'Disease',      type: 'fk', fkModel: 'diseases'                      },
    { name: 'quantity',     label: 'Quantity',     type: 'number', required: true },
    { name: 'duration',     label: 'Duration',     type: 'text'                   },
    { name: 'instructions', label: 'Instructions', type: 'textarea'               },
  ],
};


export default function ModelForm() {
  const { model, id } = useParams();
  const navigate      = useNavigate();
  const isNew         = id === 'new';
  const fields        = FORM_FIELDS[model] || [];

  const [form, setForm]         = useState({});
  const [dropdowns, setDropdowns] = useState({});
  const [search, setSearch]     = useState({});
  const [loading, setLoading]   = useState(true);
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState(null);

  // Load dropdowns + record data together
  useEffect(() => {
    const hasFk = fields.some(f => f.type === 'fk');

    const promises = [
      hasFk ? fetchDropdowns() : Promise.resolve({ data: {} }),
      isNew ? Promise.resolve(null) : crudApi.get(model, id),
    ];

    Promise.all(promises).then(([ddRes, recRes]) => {
      setDropdowns(ddRes.data || {});
      if (recRes) {
        setForm(recRes.data);
      } else {
        const defaults = {};
        fields.forEach(f => {
          defaults[f.name] = f.type === 'checkbox' ? true : '';
        });
        setForm(defaults);
      }
      setLoading(false);
    });
  }, [model, id]);

  const handleChange = (name, value) => {
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async () => {
    setSaving(true);
    setError(null);
    try {
      if (isNew) {
        await crudApi.create(model, form);
      } else {
        await crudApi.update(model, id, form);
      }
      navigate(`/admin-panel/${model}`);
    } catch (err) {
      setError(err.response?.data || 'Save failed');
      setSaving(false);
    }
  };

  const renderField = (field) => {
    if (field.type === 'textarea') {
      return (
        <textarea
          value={form[field.name] || ''}
          onChange={e => handleChange(field.name, e.target.value)}
          rows={3}
          style={inputStyle}
        />
      );
    }

    if (field.type === 'select') {
      return (
        <select
          value={form[field.name] || ''}
          onChange={e => handleChange(field.name, e.target.value)}
          style={inputStyle}
        >
          <option value="">— Select —</option>
          {field.options.map(opt => {
            const val   = typeof opt === 'object' ? opt.value : opt;
            const label = typeof opt === 'object' ? opt.label : opt;
            return <option key={val} value={val}>{label}</option>;
          })}
        </select>
      );
    }

    if (field.type === 'checkbox') {
      return (
        <label style={{ 
          display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer',
          padding: '12px 16px', background: '#f8fafc', borderRadius: 10, border: '1px solid #e2e8f0'
        }}>
          <input
            type="checkbox"
            checked={!!form[field.name]}
            onChange={e => handleChange(field.name, e.target.checked)}
            style={{ width: 18, height: 18, accentColor: '#2563eb' }}
          />
          <span style={{ fontSize: 14, fontWeight: 700, color: form[field.name] ? '#0f172a' : '#64748b' }}>
            {form[field.name] ? 'ACTIVE / YES' : 'INACTIVE / NO'}
          </span>
        </label>
      );
    }

    if (field.type === 'fk') {
      const options  = dropdowns[field.fkModel] || [];
      const searchVal = search[field.name] || '';
      const filtered  = options.filter(o =>
        o.label.toLowerCase().includes(searchVal.toLowerCase())
      );

      return (
        <div style={{ background: '#f8fafc', padding: 12, borderRadius: 10, border: '1px solid #e2e8f0' }}>
          <input
            placeholder={`Search ${field.label}...`}
            value={searchVal}
            onChange={e => setSearch(prev => ({ ...prev, [field.name]: e.target.value }))}
            style={{ ...inputStyle, marginBottom: 8, background: '#fff' }}
          />
          <select
            value={form[field.name] || ''}
            onChange={e => {
              handleChange(field.name, e.target.value ? Number(e.target.value) : '');
              setSearch(prev => ({ ...prev, [field.name]: '' }));
            }}
            size={Math.min(6, filtered.length + 1)}
            style={{
              ...inputStyle,
              height: 'auto',
              background: '#fff',
              overflowY: 'auto',
              display: filtered.length > 0 || !searchVal ? 'block' : 'none'
            }}
          >
            <option value="">— Select —</option>
            {filtered.map(opt => (
              <option key={opt.value} value={opt.value} style={{ padding: '8px' }}>
                {opt.label}
              </option>
            ))}
          </select>
          {form[field.name] && (
            <div style={{ marginTop: 10, fontSize: 12, fontWeight: 700, color: '#10b981', display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 14 }}>✓</span> {options.find(o => o.value === form[field.name])?.label || `Entry ID ${form[field.name]}`}
            </div>
          )}
        </div>
      );
    }

    return (
      <input
        type={field.type}
        value={form[field.name] ?? ''}
        onChange={e => handleChange(
          field.name,
          field.type === 'number' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value
        )}
        style={inputStyle}
      />
    );
  };

  if (loading) return (
    <div style={{ height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
      <div style={{ width: 32, height: 32, border: '4px solid #f1f5f9', borderTopColor: '#2563eb', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      <div style={{ marginTop: 16, fontSize: 15, fontWeight: 600 }}>Loading record data...</div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: 800 }}>
      <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }`}</style>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 32 }}>
        <button onClick={() => navigate(`/admin-panel/${model}`)} style={backBtnStyle}>
          <span style={{ fontSize: 18 }}>←</span> Back
        </button>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#2563eb', textTransform: 'uppercase', letterSpacing: '1px' }}>
            Resource Editor 
          </div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, color: '#0f172a', letterSpacing: '-0.75px' }}>
            {isNew ? 'New' : 'Edit'} {model.split('-').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' ')}
          </h1>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div style={{ 
          marginBottom: 24, padding: '16px 20px', background: '#fee2e2', 
          border: '1px solid #fecaca', borderRadius: 12, fontSize: 14, color: '#991b1b', 
          fontWeight: 600, boxShadow: '0 2px 4px 0 rgb(0 0 0 / 0.05)'
        }}>
          <div style={{ marginBottom: 4 }}>Submission Error</div>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.8, fontWeight: 500 }}>
            {typeof error === 'object' ? JSON.stringify(error) : error}
          </p>
        </div>
      )}

      {/* Form Card */}
      <div style={{ 
        background: '#fff', 
        borderRadius: 16, 
        padding: 40, 
        border: '1px solid #e2e8f0',
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)'
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 32 }}>
          {fields.map(field => (
            <div key={field.name} style={{ marginBottom: 8 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 700, color: '#475569', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                {field.label}
                {field.required && <span style={{ color: '#ef4444', marginLeft: 4 }}>*</span>}
              </label>
              {renderField(field)}
            </div>
          ))}
        </div>

        <div style={{ 
          display: 'flex', gap: 12, marginTop: 48, paddingTop: 24, borderTop: '1px solid #f1f5f9'
        }}>
          <button
            onClick={handleSubmit}
            disabled={saving}
            style={{
              padding: '12px 32px', borderRadius: 10, border: 'none',
              background: saving ? '#94a3b8' : '#1e293b', color: '#fff',
              fontWeight: 700, fontSize: 15, cursor: saving ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
            }}
            onMouseOver={(e) => !saving && (e.target.style.background = '#0f172a')}
            onMouseOut={(e) => !saving && (e.target.style.background = '#1e293b')}
          >
            {saving ? 'Processing...' : isNew ? 'Create Repository Entry' : 'Update Record'}
          </button>
          <button
            onClick={() => navigate(`/admin-panel/${model}`)}
            style={{ 
              padding: '12px 24px', borderRadius: 10, border: '1px solid #e2e8f0', 
              background: '#fff', fontSize: 15, fontWeight: 600, cursor: 'pointer',
              color: '#475569', transition: 'all 0.2s'
            }}
            onMouseOver={(e) => e.target.style.borderColor = '#cbd5e1'}
            onMouseOut={(e) => e.target.style.borderColor = '#e2e8f0'}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// Shared styles
const inputStyle = {
  width: '100%', padding: '12px 14px', borderRadius: 10,
  border: '1px solid #e2e8f0', fontSize: 14, fontWeight: 500,
  boxSizing: 'border-box', outline: 'none', background: '#f8fafc',
  transition: 'all 0.2s'
};

const backBtnStyle = {
  padding: '10px 16px', borderRadius: 10,
  border: '1px solid #e2e8f0', background: '#fff',
  cursor: 'pointer', fontSize: 13, fontWeight: 700,
  color: '#64748b', transition: 'all 0.2s',
  display: 'flex', alignItems: 'center', gap: 8
};