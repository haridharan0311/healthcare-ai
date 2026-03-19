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
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={!!form[field.name]}
            onChange={e => handleChange(field.name, e.target.checked)}
            style={{ width: 16, height: 16 }}
          />
          <span style={{ fontSize: 14, color: '#555' }}>
            {form[field.name] ? 'Yes' : 'No'}
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
        <div>
          {/* Search input */}
          <input
            placeholder={`Search ${field.label}...`}
            value={searchVal}
            onChange={e => setSearch(prev => ({ ...prev, [field.name]: e.target.value }))}
            style={{ ...inputStyle, marginBottom: 6 }}
          />
          {/* Dropdown */}
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
              overflowY: 'auto',
              display: filtered.length > 0 || !searchVal ? 'block' : 'none'
            }}
          >
            <option value="">— Select —</option>
            {filtered.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {/* Show selected value */}
          {form[field.name] && (
            <div style={{ marginTop: 6, fontSize: 12, color: '#1D9E75' }}>
              Selected: {options.find(o => o.value === form[field.name])?.label || `ID ${form[field.name]}`}
            </div>
          )}
        </div>
      );
    }

    // Default: text, number, date, datetime-local
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

  if (loading) return <div style={{ padding: 40, color: '#aaa' }}>Loading...</div>;

  return (
    <div style={{ padding: 32, maxWidth: 680 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 28 }}>
        <button onClick={() => navigate(`/admin-panel/${model}`)} style={backBtnStyle}>
          ← Back
        </button>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 500 }}>
          {isNew ? 'Add new' : 'Edit'} — {model.replace(/-/g, ' ')}
          {!isNew && <span style={{ fontSize: 14, color: '#888', marginLeft: 8 }}>ID: {id}</span>}
        </h1>
      </div>

      {/* Error */}
      {error && (
        <div style={{ marginBottom: 16, padding: '12px 16px', background: '#FCEBEB', border: '1px solid #F09595', borderRadius: 8, fontSize: 13, color: '#A32D2D', whiteSpace: 'pre-wrap' }}>
          {typeof error === 'object' ? JSON.stringify(error, null, 2) : error}
        </div>
      )}

      {/* Form */}
      <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #eee', padding: 28 }}>
        {fields.map(field => (
          <div key={field.name} style={{ marginBottom: 22 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#444', marginBottom: 6 }}>
              {field.label}
              {field.required && <span style={{ color: '#E24B4A', marginLeft: 4 }}>*</span>}
            </label>
            {renderField(field)}
          </div>
        ))}

        <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
          <button
            onClick={handleSubmit}
            disabled={saving}
            style={{
              padding: '10px 24px', borderRadius: 8, border: 'none',
              background: saving ? '#aaa' : '#89b4fa', color: '#1e1e2e',
              fontWeight: 500, fontSize: 14, cursor: saving ? 'not-allowed' : 'pointer'
            }}
          >
            {saving ? 'Saving...' : isNew ? 'Create' : 'Save changes'}
          </button>
          <button
            onClick={() => navigate(`/admin-panel/${model}`)}
            style={{ padding: '10px 20px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', fontSize: 14, cursor: 'pointer' }}
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
  width: '100%', padding: '8px 12px', borderRadius: 6,
  border: '1px solid #ddd', fontSize: 14,
  boxSizing: 'border-box', outline: 'none'
};

const backBtnStyle = {
  padding: '6px 14px', borderRadius: 6,
  border: '1px solid #ddd', background: '#fff',
  cursor: 'pointer', fontSize: 13
};