package com.verane.mobile.feature.customers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.verane.mobile.core.network.CustomerDto
import com.verane.mobile.core.network.CustomerPatchRequest
import com.verane.mobile.core.repository.VeraneRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CustomerForm(
    val firstName: String = "",
    val lastName: String = "",
    val city: String = "",
    val customerType: String = "",
    val interests: String = "",
    val tags: String = "",
    val notes: String = "",
    val paymentStatus: String = "",
    val paymentReference: String = "",
)

data class CustomersUiState(
    val search: String = "",
    val loading: Boolean = false,
    val saving: Boolean = false,
    val error: String = "",
    val success: String = "",
    val customers: List<CustomerDto> = emptyList(),
    val selectedPhone: String? = null,
    val selectedCustomer: CustomerDto? = null,
    val form: CustomerForm = CustomerForm(),
)

class CustomersViewModel(
    private val repository: VeraneRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(CustomersUiState())
    val uiState: StateFlow<CustomersUiState> = _uiState.asStateFlow()

    private var searchJob: Job? = null

    init {
        refreshCustomers()
    }

    fun updateSearch(value: String) {
        _uiState.update { it.copy(search = value) }
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            delay(350)
            refreshCustomers()
        }
    }

    fun refreshCustomers() {
        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, error = "", success = "") }
            runCatching {
                repository.listCustomers(search = _uiState.value.search.trim(), pageSize = 50)
            }.onSuccess { list ->
                val currentSelection = _uiState.value.selectedPhone
                val selected = when {
                    currentSelection.isNullOrBlank() -> list.firstOrNull()?.phone
                    list.any { it.phone == currentSelection } -> currentSelection
                    else -> list.firstOrNull()?.phone
                }
                _uiState.update {
                    it.copy(
                        loading = false,
                        customers = list,
                        selectedPhone = selected,
                    )
                }
                selected?.let { selectCustomer(it) }
            }.onFailure { e ->
                _uiState.update { it.copy(loading = false, error = e.message ?: "No se pudieron cargar clientes") }
            }
        }
    }

    fun selectCustomer(phone: String) {
        _uiState.update { it.copy(selectedPhone = phone, error = "", success = "") }
        viewModelScope.launch {
            runCatching { repository.getCustomer(phone) }
                .onSuccess { customer ->
                    if (customer == null) {
                        _uiState.update { it.copy(error = "Cliente no encontrado", selectedCustomer = null) }
                        return@onSuccess
                    }
                    _uiState.update {
                        it.copy(
                            selectedCustomer = customer,
                            form = customer.toForm(),
                            error = "",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message ?: "No se pudo cargar cliente") }
                }
        }
    }

    fun clearSelection() {
        _uiState.update { it.copy(selectedPhone = null, selectedCustomer = null, form = CustomerForm(), error = "") }
    }

    fun updateForm(transform: (CustomerForm) -> CustomerForm) {
        _uiState.update { it.copy(form = transform(it.form), error = "", success = "") }
    }

    fun saveCustomer() {
        val state = _uiState.value
        val phone = state.selectedPhone ?: return
        viewModelScope.launch {
            _uiState.update { it.copy(saving = true, error = "", success = "") }
            runCatching {
                repository.updateCustomer(
                    phone = phone,
                    patch = CustomerPatchRequest(
                        firstName = state.form.firstName,
                        lastName = state.form.lastName,
                        city = state.form.city,
                        customerType = state.form.customerType,
                        interests = state.form.interests,
                        tags = state.form.tags,
                        notes = state.form.notes,
                        paymentStatus = state.form.paymentStatus,
                        paymentReference = state.form.paymentReference,
                    ),
                )
            }.onSuccess { updated ->
                _uiState.update {
                    it.copy(
                        saving = false,
                        success = "Cliente guardado",
                        selectedCustomer = updated ?: it.selectedCustomer,
                        form = updated?.toForm() ?: it.form,
                    )
                }
                refreshCustomers()
            }.onFailure { e ->
                _uiState.update { it.copy(saving = false, error = e.message ?: "No se pudo guardar") }
            }
        }
    }

    private fun CustomerDto.toForm(): CustomerForm {
        return CustomerForm(
            firstName = firstName,
            lastName = lastName,
            city = city,
            customerType = customerType,
            interests = interests,
            tags = tags,
            notes = notes,
            paymentStatus = paymentStatus,
            paymentReference = paymentReference,
        )
    }
}
