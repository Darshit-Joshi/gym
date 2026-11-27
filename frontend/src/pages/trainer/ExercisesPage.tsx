import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusCircle,
  Edit2,
  Trash2,
  Dumbbell,
  CheckCircle,
  AlertCircle,
  X,
  AlertTriangle,
} from 'lucide-react';
import { exerciseService } from '../../services/api';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Select } from '../../components/common/Select';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { EmptyState } from '../../components/common/EmptyState';
import { PageHeader, SearchInput, Segmented } from '../../components/common/ui';
import type { Exercise, MuscleGroup } from '../../types';

const MUSCLE_GROUPS: MuscleGroup[] = [
  'Chest',
  'Back',
  'Shoulders',
  'Biceps',
  'Triceps',
  'Legs',
  'Core',
  'Cardio',
  'Other',
];

const EQUIPMENT_OPTIONS = [
  'All',
  'Barbell',
  'Dumbbell',
  'Cable',
  'Machine',
  'Bodyweight',
  'Cardio Machine',
  'Other',
];

const DIFFICULTY_OPTIONS = ['All', 'Beginner', 'Intermediate', 'Advanced'];

export const ExercisesPage: React.FC = () => {
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [selectedMuscleGroup, setSelectedMuscleGroup] = useState('all');
  const [selectedEquipment, setSelectedEquipment] = useState('All');
  const [selectedDifficulty, setSelectedDifficulty] = useState('All');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingExercise, setEditingExercise] = useState<Exercise | null>(null);
  const [deleteCandidate, setDeleteCandidate] = useState<Exercise | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    muscle_group: 'Chest',
    equipment: 'Barbell',
    difficulty: 'Intermediate',
    description: '',
  });

  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const { data: exercises = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['exercises', search, selectedMuscleGroup, selectedEquipment, selectedDifficulty],
    queryFn: () =>
      exerciseService.getExercises({
        search: search || undefined,
        muscle_group: selectedMuscleGroup !== 'all' ? selectedMuscleGroup : undefined,
        equipment: selectedEquipment !== 'All' ? selectedEquipment : undefined,
        difficulty: selectedDifficulty !== 'All' ? selectedDifficulty : undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => exerciseService.createExercise(data),
    onSuccess: (ex) => {
      queryClient.invalidateQueries({ queryKey: ['exercises'] });
      setIsModalOpen(false);
      resetForm();
      setNotification({ type: 'success', message: `Exercise "${ex.name}" added to library!` });
    },
    onError: (err: any) => {
      setNotification({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to create exercise.',
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      exerciseService.updateExercise(id, data),
    onSuccess: (ex) => {
      queryClient.invalidateQueries({ queryKey: ['exercises'] });
      setIsModalOpen(false);
      resetForm();
      setNotification({ type: 'success', message: `Exercise "${ex.name}" updated!` });
    },
    onError: (err: any) => {
      setNotification({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to update exercise.',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => exerciseService.deleteExercise(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exercises'] });
      setDeleteCandidate(null);
      setNotification({ type: 'success', message: 'Exercise removed from library.' });
    },
    onError: (err: any) => {
      setDeleteCandidate(null);
      setNotification({
        type: 'error',
        message:
          err.response?.data?.detail ||
          'Cannot delete exercise: it may be referenced in workout plans or recorded sessions.',
      });
    },
  });

  const resetForm = () => {
    setEditingExercise(null);
    setFormData({
      name: '',
      muscle_group: 'Chest',
      equipment: 'Barbell',
      difficulty: 'Intermediate',
      description: '',
    });
  };

  const openCreateModal = () => {
    resetForm();
    setIsModalOpen(true);
  };

  const openEditModal = (ex: Exercise) => {
    setEditingExercise(ex);
    setFormData({
      name: ex.name,
      muscle_group: ex.muscle_group,
      equipment: ex.equipment || 'Barbell',
      difficulty: ex.difficulty || 'Intermediate',
      description: ex.description || '',
    });
    setIsModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;

    const payload = {
      name: formData.name.trim(),
      muscle_group: formData.muscle_group,
      equipment: formData.equipment,
      difficulty: formData.difficulty,
      description: formData.description.trim() || undefined,
    };

    if (editingExercise) {
      updateMutation.mutate({ id: editingExercise.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const getDifficultyBadgeVariant = (diff?: string) => {
    switch (diff?.toLowerCase()) {
      case 'beginner':
        return 'lime';
      case 'intermediate':
        return 'warning';
      case 'advanced':
        return 'danger';
      default:
        return 'neutral';
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Library"
        title="Exercise library"
        description="Your movement catalog, tagged by muscle, equipment and level."
        actions={
          <Button variant="primary" leftIcon={<PlusCircle className="w-4 h-4" />} onClick={openCreateModal}>
            Add exercise
          </Button>
        }
      />

      {notification && (
        <div
          className={`p-3.5 rounded-lg text-sm flex items-center justify-between border ${
            notification.type === 'success'
              ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-300'
              : 'bg-rose-950/60 border-rose-800/80 text-rose-300'
          }`}
        >
          <div className="flex items-center space-x-2">
            {notification.type === 'success' ? (
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-[var(--color-text-secondary)] hover:text-[var(--color-text)]">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="space-y-3">
        <div className="grid grid-cols-2 md:grid-cols-[1fr_12rem_12rem] gap-3">
          <SearchInput value={search} onChange={setSearch} placeholder="Search exercises" className="col-span-2 md:col-span-1" />
          <Select
            aria-label="Equipment"
            value={selectedEquipment}
            onChange={(e) => setSelectedEquipment(e.target.value)}
            options={EQUIPMENT_OPTIONS.map((eq) => ({ value: eq, label: eq === 'All' ? 'All equipment' : eq }))}
          />
          <Select
            aria-label="Level"
            value={selectedDifficulty}
            onChange={(e) => setSelectedDifficulty(e.target.value)}
            options={DIFFICULTY_OPTIONS.map((d) => ({ value: d, label: d === 'All' ? 'All levels' : d }))}
          />
        </div>
        <Segmented
          label="Muscle group"
          size="sm"
          value={selectedMuscleGroup}
          onChange={setSelectedMuscleGroup}
          options={[{ value: 'all', label: 'All muscles' }, ...MUSCLE_GROUPS.map((mg) => ({ value: mg as string, label: mg }))]}
          className="w-fit"
        />
      </div>

      {/* Grid of Exercises */}
      {isLoading ? (
        <LoadingSpinner message="Loading exercise catalog..." />
      ) : isError ? (
        <EmptyState
          title="Failed to load exercises"
          description="Error communicating with database."
          actionLabel="Try Again"
          onAction={() => refetch()}
        />
      ) : exercises.length === 0 ? (
        <EmptyState
          icon={<Dumbbell className="w-10 h-10 text-[var(--color-primary)]" />}
          title="No Exercises Found"
          description="No exercises match your filter criteria. Try resetting filters or adding a new exercise."
          actionLabel="Add New Exercise"
          onAction={openCreateModal}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {exercises.map((ex) => (
            <Card
              key={ex.id}
              className="hover:border-[var(--color-primary)] transition-all flex flex-col justify-between p-4"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-extrabold text-[var(--color-text)] text-base leading-snug">{ex.name}</h3>
                  <div className="flex items-center -mr-2 -mt-2 sm:mr-0 sm:mt-0 shrink-0">
                    <button
                      onClick={() => openEditModal(ex)}
                      className="w-10 h-10 sm:w-8 sm:h-8 flex items-center justify-center text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] rounded-lg hover:bg-[var(--color-hover)] transition-colors cursor-pointer"
                      title="Edit exercise"
                      aria-label={`Edit ${ex.name}`}
                    >
                      <Edit2 className="w-4 h-4 sm:w-3.5 sm:h-3.5" />
                    </button>
                    <button
                      onClick={() => setDeleteCandidate(ex)}
                      className="w-10 h-10 sm:w-8 sm:h-8 flex items-center justify-center text-[var(--color-text-secondary)] hover:text-rose-400 rounded-lg hover:bg-[var(--color-hover)] transition-colors cursor-pointer"
                      title="Delete exercise"
                      aria-label={`Delete ${ex.name}`}
                    >
                      <Trash2 className="w-4 h-4 sm:w-3.5 sm:h-3.5" />
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                  <Badge variant="lime" size="sm">
                    {ex.muscle_group}
                  </Badge>
                  {ex.equipment && (
                    <Badge variant="info" size="sm">
                      {ex.equipment}
                    </Badge>
                  )}
                  {ex.difficulty && (
                    <Badge variant={getDifficultyBadgeVariant(ex.difficulty)} size="sm">
                      {ex.difficulty}
                    </Badge>
                  )}
                </div>

                {ex.description && (
                  <p className="text-xs text-[var(--color-text-secondary)] mt-2.5 line-clamp-2">{ex.description}</p>
                )}
              </div>

              <div className="hidden sm:flex mt-4 pt-3 border-t border-[var(--color-border)] items-center justify-between text-[11px] text-[var(--color-text-secondary)] font-mono">
                <span>CATALOG #{ex.id}</span>
                <span className="text-[var(--color-text-secondary)]">ONECOUNTRY Verified</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* CREATE / EDIT EXERCISE MODAL */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingExercise ? `Edit Exercise: ${editingExercise.name}` : 'Add Exercise to Library'}
        description="Provide movement details, required equipment, and difficulty classification."
        maxWidth="md"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Exercise Name"
            required
            placeholder="e.g. Bulgarian Split Squat"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              label="Target Muscle Group"
              options={MUSCLE_GROUPS.map((mg) => ({ value: mg, label: mg }))}
              value={formData.muscle_group}
              onChange={(e) => setFormData({ ...formData, muscle_group: e.target.value })}
            />

            <Select
              label="Equipment Type"
              options={EQUIPMENT_OPTIONS.filter((eq) => eq !== 'All').map((eq) => ({
                value: eq,
                label: eq,
              }))}
              value={formData.equipment}
              onChange={(e) => setFormData({ ...formData, equipment: e.target.value })}
            />
          </div>

          <Select
            label="Difficulty Level"
            options={DIFFICULTY_OPTIONS.filter((d) => d !== 'All').map((d) => ({
              value: d,
              label: d,
            }))}
            value={formData.difficulty}
            onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
          />

          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1.5">
              Coaching Notes & Setup (Optional)
            </label>
            <textarea
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="e.g. Keep chest upright, foot flat on front platform, lower until 90 degrees."
              className="w-full rounded-lg bg-[var(--color-input)] border border-[var(--color-input-border)] p-3 text-sm text-[var(--color-text)] placeholder-[var(--color-text-secondary)] focus:outline-none focus:border-[var(--color-input-focus)]"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-3 border-t border-[var(--color-border)]">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={createMutation.isPending || updateMutation.isPending}
            >
              {editingExercise ? 'Save Changes' : 'Add to Catalog'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* DELETE CONFIRMATION MODAL */}
      <Modal
        isOpen={Boolean(deleteCandidate)}
        onClose={() => setDeleteCandidate(null)}
        title="Confirm Exercise Deletion"
        maxWidth="sm"
      >
        <div className="space-y-4">
          <div className="flex items-start space-x-3 p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400 mt-0.5" />
            <div>
              <p className="font-semibold">
                Delete "{deleteCandidate?.name}"?
              </p>
              <p className="text-xs text-rose-400/80 mt-1">
                This action is irreversible. If this exercise is actively assigned in any workout routine or recorded session, deletion will be blocked to preserve athlete data integrity.
              </p>
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-3 border-t border-[var(--color-border)]">
            <Button variant="outline" onClick={() => setDeleteCandidate(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              isLoading={deleteMutation.isPending}
              onClick={() => {
                if (deleteCandidate) {
                  deleteMutation.mutate(deleteCandidate.id);
                }
              }}
            >
              Confirm Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
